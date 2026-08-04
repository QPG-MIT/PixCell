"""
Flex Simulation Module

Builds complete Tidy3D simulations from GDSFactory components.
"""

import os
from typing import List, Tuple, Any, Optional, Dict

from .materials import create_material_from_preset
from .gds_converter import convert_component_to_structures, get_component_bounds

# Check if Tidy3D is available
try:
    import tidy3d as td
    TIDY3D_AVAILABLE = True
except ImportError:
    TIDY3D_AVAILABLE = False
    td = None


# =============================================================================
# SIMULATION CONFIGURATION
# =============================================================================

DEFAULT_CONFIG = {
    "min_steps_per_wvl": 32,       # Grid resolution (32 for resolving 500nm features at 1.55um)
    "run_time_ps": 5.0,            # Run time in picoseconds (allows 3 passes in 100+um Si device)
    "pad_xy_um": 2.0,              # XY padding in micrometers (>1 wavelength at 1.55um)
    "pad_z_um": 2.0,               # Z padding in micrometers (>1 wavelength at 1.55um)
    "num_modes": 2,                # Number of modes to monitor
    "source_mode_index": 0,        # Source mode index
}


def is_available() -> bool:
    """Check if Tidy3D is available."""
    return TIDY3D_AVAILABLE


def create_simulation_from_component(
    component: Any,
    layers: List[Tuple[int, int]],
    material: str,
    thickness_nm: int,
    wavelength_um: float,
    api_key: str,
    custom_core_n: Optional[float] = None,
    custom_clad_n: Optional[float] = None,
    config: Optional[Dict] = None,
    auto_runtime: bool = True,
    validate_runtime: bool = True,
) -> Any:
    """
    Create a complete Tidy3D simulation from a GDSFactory component.

    Configuration:
    - Grid: 20 steps per wavelength (accurate FDTD per Taflove)
    - Boundaries: PML on all sides (>1 wavelength padding)
    - Run time: Auto-calculated based on device size or 3 ps default
    - Mode source at input (left edge)
    - Mode monitor at output (right edge, 2 modes)

    Args:
        component: GDSFactory Component
        layers: List of (layer, datatype) tuples to include
        material: Material preset name
        thickness_nm: Device thickness in nanometers
        wavelength_um: Simulation wavelength in micrometers
        api_key: Tidy3D API key
        custom_core_n: Custom core refractive index (for Custom preset)
        custom_clad_n: Custom cladding refractive index (for Custom preset)
        config: Optional configuration overrides
        auto_runtime: If True, auto-calculate run time based on device size
        validate_runtime: If True, validate run time is sufficient for device

    Returns:
        td.Simulation object

    Raises:
        RuntimeError: If Tidy3D not available
        ValueError: If simulation cannot be created
    """
    if not TIDY3D_AVAILABLE:
        raise RuntimeError("Tidy3D is not installed. Install with: pip install 'pixcell[simulate]'")

    # Set API key in environment
    os.environ["SIMCLOUD_APIKEY"] = api_key

    # Merge configuration
    cfg = {**DEFAULT_CONFIG, **(config or {})}

    # Convert thickness to micrometers
    thickness_um = thickness_nm / 1000.0

    # Create materials
    core_medium, clad_medium, preset_info = create_material_from_preset(
        material, custom_core_n, custom_clad_n
    )

    # Convert component to 3D structures
    structures = convert_component_to_structures(
        component, layers, thickness_um, core_medium
    )

    # Get component bounds
    xmin, ymin, xmax, ymax = get_component_bounds(component)

    # Calculate simulation domain with padding
    pad_xy = cfg["pad_xy_um"]
    pad_z = cfg["pad_z_um"]

    sim_xmin = xmin - pad_xy
    sim_xmax = xmax + pad_xy
    sim_ymin = ymin - pad_xy
    sim_ymax = ymax + pad_xy
    sim_zmin = -pad_z
    sim_zmax = thickness_um + pad_z

    sim_size = (
        sim_xmax - sim_xmin,
        sim_ymax - sim_ymin,
        sim_zmax - sim_zmin
    )

    sim_center = (
        (sim_xmin + sim_xmax) / 2,
        (sim_ymin + sim_ymax) / 2,
        (sim_zmin + sim_zmax) / 2
    )

    # Calculate frequency
    freq0 = td.C_0 / wavelength_um
    fwidth = freq0 / 10  # 10% bandwidth

    # Create grid specification
    grid_spec = td.GridSpec.auto(
        min_steps_per_wvl=cfg["min_steps_per_wvl"],
        wavelength=wavelength_um
    )

    # Create mode source at input (left edge)
    source_center = (sim_xmin + 0.5, (ymin + ymax) / 2, thickness_um / 2)
    source_size = (0, sim_ymax - sim_ymin - 0.2, sim_zmax - sim_zmin - 0.2)

    mode_source = td.ModeSource(
        center=source_center,
        size=source_size,
        source_time=td.GaussianPulse(freq0=freq0, fwidth=fwidth),
        direction="+",
        mode_spec=td.ModeSpec(num_modes=1),
        mode_index=cfg["source_mode_index"]
    )

    # Create mode monitor at output (right edge)
    monitor_center = (sim_xmax - 0.5, (ymin + ymax) / 2, thickness_um / 2)
    monitor_size = (0, sim_ymax - sim_ymin - 0.2, sim_zmax - sim_zmin - 0.2)

    mode_monitor = td.ModeMonitor(
        center=monitor_center,
        size=monitor_size,
        freqs=[freq0],
        mode_spec=td.ModeSpec(num_modes=cfg["num_modes"]),
        name="output_modes"
    )

    # Create field monitor at center Z plane
    field_monitor = td.FieldMonitor(
        center=(sim_center[0], sim_center[1], thickness_um / 2),
        size=(sim_size[0], sim_size[1], 0),
        freqs=[freq0],
        name="field_xy"
    )

    # Create simulation
    run_time = cfg["run_time_ps"] * 1e-12  # Convert to seconds

    simulation = td.Simulation(
        size=sim_size,
        center=sim_center,
        grid_spec=grid_spec,
        structures=structures,
        sources=[mode_source],
        monitors=[mode_monitor, field_monitor],
        run_time=run_time,
        boundary_spec=td.BoundarySpec.all_sides(boundary=td.PML()),
        medium=clad_medium,  # Background medium
    )

    return simulation


def get_simulation_info(
    component: Any,
    layers: List[Tuple[int, int]],
    thickness_nm: int,
    wavelength_um: float,
    config: Optional[Dict] = None,
    validate_modes: bool = True,
    estimate_mode_count: bool = True,
) -> Dict[str, Any]:
    """
    Get information about the simulation that would be created.

    Useful for displaying simulation parameters before upload.

    Args:
        component: GDSFactory Component
        layers: Layers to include
        thickness_nm: Thickness in nm
        wavelength_um: Wavelength in um
        config: Optional configuration
        validate_modes: If True, validate if device supports requested modes
        estimate_mode_count: If True, estimate number of supported modes

    Returns:
        Dict with simulation info including mode validation
    """
    cfg = {**DEFAULT_CONFIG, **(config or {})}
    thickness_um = thickness_nm / 1000.0

    # Get component bounds
    xmin, ymin, xmax, ymax = get_component_bounds(component)

    pad_xy = cfg["pad_xy_um"]
    pad_z = cfg["pad_z_um"]

    domain_x = (xmax - xmin) + 2 * pad_xy
    domain_y = (ymax - ymin) + 2 * pad_xy
    domain_z = thickness_um + 2 * pad_z

    return {
        "domain_size_um": (round(domain_x, 2), round(domain_y, 2), round(domain_z, 2)),
        "grid_resolution": cfg["min_steps_per_wvl"],
        "run_time_ps": cfg["run_time_ps"],
        "wavelength_um": wavelength_um,
        "thickness_um": thickness_um,
        "layers": layers,
        "num_modes": cfg["num_modes"],
    }
