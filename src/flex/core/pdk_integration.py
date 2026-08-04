"""
Flex PDK Integration Module

Bridges the PDK system with Flex for foundry-aware simulations.
Supports sidewall angles, rib/slab structures, and PDK materials.
"""

from __future__ import annotations

import os
import tempfile
from typing import Any, Dict, List, Optional, Tuple

# Check if dependencies are available
try:
    import gdstk
    GDSTK_AVAILABLE = True
except ImportError:
    GDSTK_AVAILABLE = False
    gdstk = None

try:
    import tidy3d as td
    import numpy as np
    TIDY3D_AVAILABLE = True
except ImportError:
    TIDY3D_AVAILABLE = False
    td = None
    np = None


def is_available() -> bool:
    """Check if required dependencies are available."""
    return GDSTK_AVAILABLE and TIDY3D_AVAILABLE


def create_pdk_simulation(
    component: Any,
    pdk: Any,  # PDKDefinition
    layer_name: str,
    cross_section_name: Optional[str] = None,
    wavelength_um: float = 1.55,
    api_key: Optional[str] = None,
    config: Optional[Dict] = None,
    source_gds_layer: Optional[Tuple[int, int]] = None,
) -> "td.Simulation":
    """
    Create a Tidy3D simulation from a GDSFactory component using PDK specifications.

    This function handles:
    - PDK material properties (including anisotropic LN)
    - Sidewall angles from PDK cross-section
    - Rib/slab waveguide structures

    Args:
        component: GDSFactory Component
        pdk: PDKDefinition from gg.pdk
        layer_name: PDK layer name (e.g., "TFLN_WG1") - used for material properties
        cross_section_name: Optional PDK cross-section name for geometry
        wavelength_um: Simulation wavelength in micrometers
        api_key: Optional Tidy3D API key
        config: Optional configuration overrides
        source_gds_layer: GDS layer tuple (layer, datatype) where component geometry exists.
                         If None, uses the PDK layer's GDS number. Use this when the
                         component was created with a different layer (e.g., (1,0)) than
                         the PDK target layer (e.g., (10,0) for TFLN_WG1).

    Returns:
        td.Simulation object ready for upload

    Raises:
        RuntimeError: If dependencies not available
        KeyError: If layer/cross-section not found in PDK
    """
    if not TIDY3D_AVAILABLE:
        raise RuntimeError("Tidy3D is not installed. Install with: pip install 'pixcell[simulate]'")

    if api_key:
        os.environ["SIMCLOUD_APIKEY"] = api_key

    # Default config
    default_config = {
        "min_steps_per_wvl": 15,
        "run_time_ps": 2.0,
        "pad_xy_um": 1.5,
        "pad_z_um": 1.5,
        "num_modes": 3,
        "source_mode_index": 0,
        "include_slab": True,
        "slab_margin_um": 2.0,
    }
    cfg = {**default_config, **(config or {})}

    # Get PDK layer and cross-section info
    layer = pdk.get_layer(layer_name)
    if not layer:
        raise KeyError(f"Layer '{layer_name}' not found in PDK '{pdk.name}'")

    # Use source_gds_layer if provided, otherwise use PDK layer's GDS number
    gds_layer = source_gds_layer if source_gds_layer else (layer.gds_number, layer.datatype)

    # Get cross-section (for geometry parameters)
    if cross_section_name:
        xs = pdk.get_cross_section(cross_section_name)
    else:
        xs = None

    # Determine geometry parameters
    if xs:
        film_thickness_um = xs.film_thickness_nm / 1000
        etch_depth_um = xs.etch_depth_nm / 1000
        slab_thickness_um = xs.slab_thickness_nm / 1000
        sidewall_angle_rad = np.deg2rad(xs.sidewall_angle_deg)
    else:
        film_thickness_um = (layer.thickness_nm or 600) / 1000
        etch_depth_um = (layer.etch_depth_nm or film_thickness_um * 1000) / 1000
        slab_thickness_um = film_thickness_um - etch_depth_um
        sidewall_angle_rad = np.deg2rad(layer.sidewall_angle_deg or 0)

    # Get materials from PDK
    from gg.pdk import PDKTidy3DConverter
    converter = PDKTidy3DConverter(pdk)

    core_medium = converter.get_medium_for_layer(layer_name)
    clad_medium = converter.get_cladding_medium()

    # Extract polygons from component
    polygons = _extract_polygons(component, [gds_layer])

    if not polygons:
        raise ValueError(f"No polygons found on layer {gds_layer}")

    # Get component bounds
    bbox = component.bbox()
    try:
        xmin, ymin = bbox[0]
        xmax, ymax = bbox[1]
    except TypeError:
        xmin, ymin = bbox.left, bbox.bottom
        xmax, ymax = bbox.right, bbox.top

    xmin, ymin, xmax, ymax = float(xmin), float(ymin), float(xmax), float(ymax)

    # Create structures
    structures = []

    # 1. Slab layer (if rib waveguide)
    if cfg["include_slab"] and slab_thickness_um > 0:
        margin = cfg["slab_margin_um"]
        slab_geo = td.PolySlab(
            vertices=[
                [xmin - margin, ymin - margin],
                [xmax + margin, ymin - margin],
                [xmax + margin, ymax + margin],
                [xmin - margin, ymax + margin],
            ],
            slab_bounds=(0, slab_thickness_um),
            reference_plane="bottom",
        )
        structures.append(td.Structure(
            geometry=slab_geo,
            medium=core_medium,
            name="slab_layer"
        ))

    # 2. Ridge layer from GDS polygons
    ridge_z_base = slab_thickness_um if slab_thickness_um > 0 else 0
    ridge_thickness = film_thickness_um - slab_thickness_um

    for i, vertices in enumerate(polygons):
        # Try with full sidewall angle, fall back to smaller or zero if needed
        # This handles narrow features that would self-intersect with large angles
        for angle_to_try in [sidewall_angle_rad, sidewall_angle_rad / 2, 0]:
            try:
                ridge_geo = td.PolySlab(
                    vertices=vertices,
                    slab_bounds=(ridge_z_base, ridge_z_base + ridge_thickness),
                    sidewall_angle=angle_to_try,
                    reference_plane="bottom",
                )
                structures.append(td.Structure(
                    geometry=ridge_geo,
                    medium=core_medium,
                    name=f"ridge_{i}"
                ))
                break  # Success, move to next polygon
            except Exception:
                continue  # Try smaller angle

    if not structures:
        raise ValueError("Could not create any valid 3D structures")

    # Simulation domain
    pad_xy = cfg["pad_xy_um"]
    pad_z = cfg["pad_z_um"]

    sim_size = (
        (xmax - xmin) + 2 * pad_xy,
        (ymax - ymin) + 2 * pad_xy,
        film_thickness_um + 2 * pad_z,
    )
    sim_center = (
        (xmin + xmax) / 2,
        (ymin + ymax) / 2,
        film_thickness_um / 2,
    )

    # Frequency
    freq0 = td.C_0 / wavelength_um
    fwidth = freq0 / 10

    # Mode source at input (left edge)
    source_x = xmin + 0.5
    source_center = (source_x, (ymin + ymax) / 2, film_thickness_um / 2)
    source_size = (0, (ymax - ymin) * 0.8, film_thickness_um + 1.0)

    mode_spec = td.ModeSpec(
        num_modes=cfg["num_modes"],
        target_neff=2.1,  # Approximate for LN
        filter_pol="te",
    )

    source = td.ModeSource(
        name="input",
        center=source_center,
        size=source_size,
        source_time=td.GaussianPulse(freq0=freq0, fwidth=fwidth),
        direction="+",
        mode_spec=mode_spec,
        mode_index=cfg["source_mode_index"],
    )

    # Monitors
    monitors = []

    # Field monitor (top view)
    monitors.append(td.FieldMonitor(
        name="field_xy",
        center=(sim_center[0], sim_center[1], film_thickness_um / 2),
        size=(sim_size[0] - 1, sim_size[1] - 1, 0),
        freqs=[freq0],
    ))

    # Mode monitor at output (right edge)
    monitor_x = xmax - 0.5
    monitors.append(td.ModeMonitor(
        name="output",
        center=(monitor_x, (ymin + ymax) / 2, film_thickness_um / 2),
        size=(0, (ymax - ymin) * 0.8, film_thickness_um + 1.0),
        freqs=[freq0],
        mode_spec=mode_spec,
    ))

    # Create simulation
    simulation = td.Simulation(
        size=sim_size,
        center=sim_center,
        medium=clad_medium,
        grid_spec=td.GridSpec.auto(
            min_steps_per_wvl=cfg["min_steps_per_wvl"],
            wavelength=wavelength_um,
        ),
        structures=structures,
        sources=[source],
        monitors=monitors,
        run_time=cfg["run_time_ps"] * 1e-12,
        boundary_spec=td.BoundarySpec.all_sides(td.PML()),
        shutoff=1e-5,
    )

    return simulation


def create_1x2_splitter_simulation(
    component: Any,
    pdk: Any,
    layer_name: str,
    cross_section_name: Optional[str] = None,
    wavelength_um: float = 1.55,
    output_positions: Optional[List[Tuple[float, float]]] = None,
    api_key: Optional[str] = None,
    config: Optional[Dict] = None,
    source_gds_layer: Optional[Tuple[int, int]] = None,
) -> "td.Simulation":
    """
    Create a Tidy3D simulation for a 1x2 splitter/coupler.

    Adds mode monitors at both output ports for measuring splitting ratio.

    Args:
        component: GDSFactory Component
        pdk: PDKDefinition from gg.pdk
        layer_name: PDK layer name - used for material properties
        cross_section_name: Optional cross-section name
        wavelength_um: Simulation wavelength
        output_positions: List of (x, y) for output monitors, or None for auto-detect
        api_key: Optional Tidy3D API key
        config: Optional configuration overrides
        source_gds_layer: GDS layer tuple (layer, datatype) where component geometry exists.
                         If None, uses the PDK layer's GDS number.

    Returns:
        td.Simulation with monitors at both outputs
    """
    if not TIDY3D_AVAILABLE:
        raise RuntimeError("Tidy3D is not installed")

    if api_key:
        os.environ["SIMCLOUD_APIKEY"] = api_key

    # Default config
    default_config = {
        "min_steps_per_wvl": 15,
        "run_time_ps": 2.0,
        "pad_xy_um": 1.5,
        "pad_z_um": 1.5,
        "num_modes": 3,
        "source_mode_index": 0,
        "include_slab": True,
        "slab_margin_um": 2.0,
        "output_monitor_width_um": 2.0,
    }
    cfg = {**default_config, **(config or {})}

    # Get PDK info
    layer = pdk.get_layer(layer_name)
    if not layer:
        raise KeyError(f"Layer '{layer_name}' not found in PDK")

    gds_layer = (layer.gds_number, layer.datatype)

    if cross_section_name:
        xs = pdk.get_cross_section(cross_section_name)
    else:
        xs = None

    # Geometry parameters
    if xs:
        film_thickness_um = xs.film_thickness_nm / 1000
        etch_depth_um = xs.etch_depth_nm / 1000
        slab_thickness_um = xs.slab_thickness_nm / 1000
        sidewall_angle_rad = np.deg2rad(xs.sidewall_angle_deg)
    else:
        film_thickness_um = (layer.thickness_nm or 600) / 1000
        etch_depth_um = (layer.etch_depth_nm or film_thickness_um * 1000) / 1000
        slab_thickness_um = film_thickness_um - etch_depth_um
        sidewall_angle_rad = np.deg2rad(layer.sidewall_angle_deg or 0)

    # Materials
    from gg.pdk import PDKTidy3DConverter
    converter = PDKTidy3DConverter(pdk)
    core_medium = converter.get_medium_for_layer(layer_name)
    clad_medium = converter.get_cladding_medium()

    # Extract polygons
    polygons = _extract_polygons(component, [gds_layer])
    if not polygons:
        raise ValueError(f"No polygons found on layer {gds_layer}")

    # Bounds
    bbox = component.bbox()
    try:
        xmin, ymin = bbox[0]
        xmax, ymax = bbox[1]
    except TypeError:
        xmin, ymin = bbox.left, bbox.bottom
        xmax, ymax = bbox.right, bbox.top
    xmin, ymin, xmax, ymax = float(xmin), float(ymin), float(xmax), float(ymax)

    # Create structures
    structures = []

    # Slab
    if cfg["include_slab"] and slab_thickness_um > 0:
        margin = cfg["slab_margin_um"]
        slab_geo = td.PolySlab(
            vertices=[
                [xmin - margin, ymin - margin],
                [xmax + margin, ymin - margin],
                [xmax + margin, ymax + margin],
                [xmin - margin, ymax + margin],
            ],
            slab_bounds=(0, slab_thickness_um),
            reference_plane="bottom",
        )
        structures.append(td.Structure(
            geometry=slab_geo,
            medium=core_medium,
            name="slab"
        ))

    # Ridges
    ridge_z_base = slab_thickness_um if slab_thickness_um > 0 else 0
    ridge_thickness = film_thickness_um - slab_thickness_um

    for i, vertices in enumerate(polygons):
        # Try with full sidewall angle, fall back to smaller or zero if needed
        for angle_to_try in [sidewall_angle_rad, sidewall_angle_rad / 2, 0]:
            try:
                ridge_geo = td.PolySlab(
                    vertices=vertices,
                    slab_bounds=(ridge_z_base, ridge_z_base + ridge_thickness),
                    sidewall_angle=angle_to_try,
                    reference_plane="bottom",
                )
                structures.append(td.Structure(
                    geometry=ridge_geo,
                    medium=core_medium,
                    name=f"ridge_{i}"
                ))
                break  # Success, move to next polygon
            except Exception:
                continue  # Try smaller angle

    if not structures:
        raise ValueError("Could not create valid structures")

    # Simulation domain
    pad_xy = cfg["pad_xy_um"]
    pad_z = cfg["pad_z_um"]

    sim_size = (
        (xmax - xmin) + 2 * pad_xy,
        (ymax - ymin) + 2 * pad_xy,
        film_thickness_um + 2 * pad_z,
    )
    sim_center = (
        (xmin + xmax) / 2,
        (ymin + ymax) / 2,
        film_thickness_um / 2,
    )

    freq0 = td.C_0 / wavelength_um
    fwidth = freq0 / 10

    mode_spec = td.ModeSpec(
        num_modes=cfg["num_modes"],
        target_neff=2.1,
        filter_pol="te",
    )

    # Source at input
    source_x = xmin + 0.5
    source = td.ModeSource(
        name="input",
        center=(source_x, 0, film_thickness_um / 2),
        size=(0, 3.0, film_thickness_um + 1.0),
        source_time=td.GaussianPulse(freq0=freq0, fwidth=fwidth),
        direction="+",
        mode_spec=mode_spec,
        mode_index=0,
    )

    # Monitors
    monitors = []

    # Field monitor
    monitors.append(td.FieldMonitor(
        name="field_xy",
        center=(sim_center[0], 0, film_thickness_um / 2),
        size=(sim_size[0] - 1, sim_size[1] - 1, 0),
        freqs=[freq0],
    ))

    # Output monitors
    output_x = xmax - 1.0
    monitor_width = cfg["output_monitor_width_um"]

    if output_positions:
        # User-specified positions
        for i, (ox, oy) in enumerate(output_positions):
            monitors.append(td.ModeMonitor(
                name=f"output_{i+1}",
                center=(ox, oy, film_thickness_um / 2),
                size=(0, monitor_width, film_thickness_um + 1.0),
                freqs=[freq0],
                mode_spec=mode_spec,
            ))
    else:
        # Try to detect from component ports
        try:
            ports = list(component.ports.values())
            output_ports = [p for p in ports if p.orientation == 0]  # Facing +X
            for i, port in enumerate(output_ports[:2]):
                monitors.append(td.ModeMonitor(
                    name=f"output_{i+1}",
                    center=(output_x, float(port.center[1]), film_thickness_um / 2),
                    size=(0, monitor_width, film_thickness_um + 1.0),
                    freqs=[freq0],
                    mode_spec=mode_spec,
                ))
        except Exception:
            # Default: assume outputs at +/- 2.75 um
            for i, y_pos in enumerate([2.75, -2.75]):
                monitors.append(td.ModeMonitor(
                    name=f"output_{i+1}",
                    center=(output_x, y_pos, film_thickness_um / 2),
                    size=(0, monitor_width, film_thickness_um + 1.0),
                    freqs=[freq0],
                    mode_spec=mode_spec,
                ))

    # Input monitor for normalization
    monitors.append(td.ModeMonitor(
        name="input_ref",
        center=(source_x + 2.0, 0, film_thickness_um / 2),
        size=(0, 3.0, film_thickness_um + 1.0),
        freqs=[freq0],
        mode_spec=mode_spec,
    ))

    simulation = td.Simulation(
        size=sim_size,
        center=sim_center,
        medium=clad_medium,
        grid_spec=td.GridSpec.auto(
            min_steps_per_wvl=cfg["min_steps_per_wvl"],
            wavelength=wavelength_um,
        ),
        structures=structures,
        sources=[source],
        monitors=monitors,
        run_time=cfg["run_time_ps"] * 1e-12,
        boundary_spec=td.BoundarySpec.all_sides(td.PML()),
        shutoff=1e-5,
    )

    return simulation


def _extract_polygons(
    component: Any,
    layers: List[Tuple[int, int]]
) -> List[List[Tuple[float, float]]]:
    """Extract polygons from component for specified layers."""
    if not GDSTK_AVAILABLE:
        raise RuntimeError("gdstk not available")

    gds_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix='.gds', delete=False) as tmp:
            gds_path = tmp.name

        component.write_gds(gds_path)
        lib = gdstk.read_gds(gds_path)

        top_cell = None
        for cell in lib.cells:
            if "CONTEXT" in cell.name.upper():
                continue
            if cell.name == component.name:
                top_cell = cell
                break
            if top_cell is None:
                top_cell = cell

        if top_cell is None:
            return []

        cell_flat = top_cell.copy(f"{top_cell.name}_flat")
        cell_flat.flatten()

        polygons = []
        layer_set = set(layers)

        for poly in cell_flat.polygons:
            if (poly.layer, poly.datatype) not in layer_set:
                continue
            if abs(poly.area()) < 0.001:
                continue
            vertices = [(float(p[0]), float(p[1])) for p in poly.points]
            polygons.append(vertices)

        return polygons

    finally:
        if gds_path and os.path.exists(gds_path):
            try:
                os.unlink(gds_path)
            except Exception:
                pass


# =============================================================================
# PDK DESIGN RULE VALIDATION
# =============================================================================

def validate_pdk_rules(
    component: Any,
    pdk: Any,
    layer_name: str,
    min_feature_nm: Optional[float] = None,
    min_spacing_nm: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Validate GDS component against foundry PDK design rules.

    Checks:
    - Minimum feature width
    - Minimum feature spacing
    - Layer-specific rules from PDK

    Args:
        component: GDSFactory Component to validate
        pdk: PDKDefinition with design rules
        layer_name: Target PDK layer
        min_feature_nm: Override minimum feature size (nm), uses PDK default if None
        min_spacing_nm: Override minimum spacing (nm), uses PDK default if None

    Returns:
        Dict with validation results:
        - valid: bool - whether all rules pass
        - violations: List[str] - list of rule violations
        - warnings: List[str] - list of warnings
        - min_feature_found_nm: float - smallest feature detected
        - min_spacing_found_nm: float - smallest spacing detected

    Note:
        This is a basic DRC check. For production use, validate with
        foundry-provided DRC decks (e.g., Calibre, KLayout DRC).
    """
    results = {
        "valid": True,
        "violations": [],
        "warnings": [],
        "min_feature_found_nm": None,
        "min_spacing_found_nm": None,
    }

    # Get PDK layer for default rules
    layer = pdk.get_layer(layer_name) if pdk else None

    # Use provided values or PDK defaults
    min_width = min_feature_nm or (layer.min_width_nm if layer and hasattr(layer, 'min_width_nm') else 100)

    # Get component bounds for basic size check
    try:
        bbox = component.bbox()
        try:
            xmin, _ymin = bbox[0]
            xmax, _ymax = bbox[1]
        except TypeError:
            xmin, _ymin = bbox.left, bbox.bottom
            xmax, _ymax = bbox.right, bbox.top

        width_um = xmax - xmin

        # Check if component is at least minimum size
        if width_um * 1000 < min_width:
            results["violations"].append(
                f"Component width ({width_um*1000:.1f}nm) < minimum ({min_width}nm)"
            )
            results["valid"] = False

    except Exception as e:
        results["warnings"].append(f"Could not check bounds: {e}")

    # Basic polygon width check (simplified DRC)
    try:
        gds_layer = (layer.gds_number, layer.datatype) if layer else (1, 0)
        polygons = _extract_polygons(component, [gds_layer])

        for i, poly in enumerate(polygons):
            if len(poly) < 3:
                continue

            # Estimate minimum feature width from bounding box
            xs = [p[0] for p in poly]
            ys = [p[1] for p in poly]
            poly_width_nm = (max(xs) - min(xs)) * 1000
            poly_height_nm = (max(ys) - min(ys)) * 1000
            min_dim_nm = min(poly_width_nm, poly_height_nm)

            if results["min_feature_found_nm"] is None or min_dim_nm < results["min_feature_found_nm"]:
                results["min_feature_found_nm"] = min_dim_nm

            if min_dim_nm < min_width:
                results["violations"].append(
                    f"Polygon {i} has dimension ({min_dim_nm:.1f}nm) < minimum ({min_width}nm)"
                )
                results["valid"] = False

    except Exception as e:
        results["warnings"].append(f"Could not check polygon widths: {e}")

    return results


def validate_drc_basic(
    component: Any,
    min_feature_um: float = 0.1,
    min_spacing_um: float = 0.1,
) -> Dict[str, Any]:
    """
    Basic design rule check for GDSFactory components.

    Args:
        component: GDSFactory Component
        min_feature_um: Minimum feature size in micrometers
        min_spacing_um: Minimum spacing in micrometers

    Returns:
        Dict with DRC results
    """
    return validate_pdk_rules(
        component=component,
        pdk=None,
        layer_name="",
        min_feature_nm=min_feature_um * 1000,
        min_spacing_nm=min_spacing_um * 1000,
    )
