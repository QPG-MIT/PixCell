"""
Tidy3D Integration for Weber Explorers

Provides optional FDTD simulation upload to Tidy3D cloud.
This module is only loaded when Tidy3D integration is enabled.
"""

import os
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any

# Check if tidy3d is available
TIDY3D_AVAILABLE = False
try:
    import gdstk
    import tidy3d as td
    import tidy3d.web as web
    TIDY3D_AVAILABLE = True
except ImportError:
    td = None
    web = None
    gdstk = None


# =============================================================================
# MATERIAL PRESETS
# =============================================================================

MATERIAL_PRESETS = {
    "Silicon (SOI)": {
        "core_n": 3.47,
        "clad_n": 1.47,
        "default_thickness": 220,
        "anisotropic": False,
        "description": "Standard silicon-on-insulator platform"
    },
    "Lithium Niobate": {
        "n_e": 2.138,
        "n_o": 2.211,
        "clad_n": 1.44,
        "default_thickness": 400,
        "anisotropic": True,
        "description": "Thin-film LN for electro-optic devices"
    },
    "Silicon Nitride": {
        "core_n": 2.0,
        "clad_n": 1.47,
        "default_thickness": 400,
        "anisotropic": False,
        "description": "Low-loss SiN platform"
    },
    "Custom": {
        "core_n": 2.5,
        "clad_n": 1.45,
        "default_thickness": 300,
        "anisotropic": False,
        "description": "User-defined material properties"
    }
}


def is_available() -> bool:
    """Check if Tidy3D integration is available."""
    return TIDY3D_AVAILABLE


def get_material_medium(material_name: str, custom_n: Optional[float] = None) -> Any:
    """
    Get Tidy3D medium for a given material preset.
    """
    if not TIDY3D_AVAILABLE:
        raise RuntimeError("Tidy3D is not installed")

    preset = MATERIAL_PRESETS.get(material_name, MATERIAL_PRESETS["Silicon (SOI)"])

    if material_name == "Custom" and custom_n is not None:
        return td.Medium(permittivity=custom_n**2, name="Custom")

    if preset.get("anisotropic"):
        n_e = preset["n_e"]
        n_o = preset["n_o"]
        medium_e = td.Medium(permittivity=n_e**2)
        medium_o = td.Medium(permittivity=n_o**2)
        return td.AnisotropicMedium(
            xx=medium_o, yy=medium_e, zz=medium_o,
            name="LiNbO3_Xcut"
        )
    else:
        return td.Medium(
            permittivity=preset["core_n"]**2,
            name=material_name.replace(" ", "_").replace("(", "").replace(")", "")
        )


def get_cladding_medium(material_name: str, custom_n: Optional[float] = None) -> Any:
    """Get cladding medium for a given material preset."""
    if not TIDY3D_AVAILABLE:
        raise RuntimeError("Tidy3D is not installed")

    preset = MATERIAL_PRESETS.get(material_name, MATERIAL_PRESETS["Silicon (SOI)"])

    if material_name == "Custom" and custom_n is not None:
        return td.Medium(permittivity=custom_n**2, name="CustomClad")

    return td.Medium(
        permittivity=preset["clad_n"]**2,
        name="SiO2_cladding"
    )


def extract_polygons_from_component(
    component: Any,
    included_layers: List[Tuple[int, int]]
) -> List[List[Tuple[float, float]]]:
    """
    Extract polygons from a GDSFactory component.
    """
    if not TIDY3D_AVAILABLE:
        raise RuntimeError("Tidy3D/gdstk is not installed")

    polygons = []

    # Export to temporary GDS
    with tempfile.NamedTemporaryFile(suffix='.gds', delete=False) as tmp:
        gds_path = tmp.name
    component.write_gds(gds_path)

    # Read with gdstk
    lib = gdstk.read_gds(gds_path)

    # Find top-level cell
    top_cell = None
    component_name = component.name

    for cell in lib.cells:
        if "CONTEXT" in cell.name.upper():
            continue
        if cell.name == component_name:
            top_cell = cell
            break
        if top_cell is None:
            top_cell = cell

    if top_cell is None:
        try:
            os.unlink(gds_path)
        except Exception:
            pass
        return polygons

    # Flatten and extract
    cell_flat = top_cell.copy(f"{top_cell.name}_flat")
    cell_flat.flatten()

    for poly in cell_flat.polygons:
        layer_dt = (poly.layer, poly.datatype)
        if layer_dt in included_layers:
            area = abs(poly.area())
            if area < 0.001:
                continue
            vertices = [(float(p[0]), float(p[1])) for p in poly.points]
            polygons.append(vertices)

    try:
        os.unlink(gds_path)
    except Exception:
        pass

    return polygons


def create_simulation_from_component(
    component: Any,
    layers: List[Tuple[int, int]],
    material: str,
    thickness_nm: float,
    wavelength_um: float,
    api_key: str,
    custom_core_n: Optional[float] = None,
    custom_clad_n: Optional[float] = None
) -> Any:
    """
    Create a Tidy3D simulation from a GDSFactory component.
    """
    if not TIDY3D_AVAILABLE:
        raise RuntimeError("Tidy3D is not installed")

    os.environ["SIMCLOUD_APIKEY"] = api_key

    thickness_um = thickness_nm / 1000.0

    if material == "Custom":
        core_medium = get_material_medium("Custom", custom_core_n)
        clad_medium = get_cladding_medium("Custom", custom_clad_n)
    else:
        core_medium = get_material_medium(material)
        clad_medium = get_cladding_medium(material)

    if not layers:
        layers = [(1, 0), (2, 0), (3, 0)]

    polygon_vertices = extract_polygons_from_component(component, layers)

    if not polygon_vertices:
        raise ValueError("No polygons found in component for selected layers")

    structures = []
    for vertices in polygon_vertices:
        try:
            slab = td.PolySlab(
                vertices=vertices,
                axis=2,
                slab_bounds=(0, thickness_um)
            )
            structures.append(td.Structure(geometry=slab, medium=core_medium))
        except Exception:
            continue

    if not structures:
        raise ValueError("Could not create any valid structures from polygons")

    xmin = component.xmin
    ymin = component.ymin
    xmax = component.xmax
    ymax = component.ymax

    pad_xy = 1.0
    pad_z = 1.0

    sim_size = (
        xmax - xmin + 2 * pad_xy,
        ymax - ymin + 2 * pad_xy,
        thickness_um + 2 * pad_z
    )

    sim_center = (
        (xmax + xmin) / 2,
        (ymax + ymin) / 2,
        thickness_um / 2
    )

    freq0 = td.C_0 / wavelength_um

    mode_source = td.ModeSource(
        center=(xmin + 0.5, (ymax + ymin) / 2, thickness_um / 2),
        size=(0, ymax - ymin + 1, thickness_um + 1),
        source_time=td.GaussianPulse(freq0=freq0, fwidth=freq0 / 10),
        direction="+",
        mode_spec=td.ModeSpec(num_modes=1),
        mode_index=0,
        name="input_mode"
    )

    output_monitor = td.ModeMonitor(
        center=(xmax - 0.5, (ymax + ymin) / 2, thickness_um / 2),
        size=(0, ymax - ymin + 1, thickness_um + 1),
        freqs=[freq0],
        mode_spec=td.ModeSpec(num_modes=2),
        name="output_monitor"
    )

    sim = td.Simulation(
        size=sim_size,
        center=sim_center,
        grid_spec=td.GridSpec.auto(min_steps_per_wvl=12, wavelength=wavelength_um),
        structures=structures,
        sources=[mode_source],
        monitors=[output_monitor],
        run_time=1e-12,
        boundary_spec=td.BoundarySpec.all_sides(boundary=td.PML()),
        medium=clad_medium
    )

    return sim


def upload_simulation(
    sim: Any,
    task_name: str = "Weber_Device"
) -> Tuple[str, str]:
    """
    Upload simulation to Tidy3D cloud.
    """
    if not TIDY3D_AVAILABLE:
        raise RuntimeError("Tidy3D is not installed")

    clean_name = task_name.replace(" ", "_")[:50]
    task_id = web.upload(sim, task_name=f"Weber_{clean_name}")
    web_url = f"https://tidy3d.simulation.cloud/workbench?taskId={task_id}"

    return task_id, web_url


def estimate_simulation_cost(task_id: str) -> Optional[float]:
    """Estimate the cost of a simulation in FlexCredits."""
    if not TIDY3D_AVAILABLE:
        return None
    try:
        return web.estimate_cost(task_id)
    except Exception:
        return None


def get_task_status(task_id: str) -> Optional[str]:
    """Get the status of an uploaded task."""
    if not TIDY3D_AVAILABLE:
        return None
    try:
        info = web.get_info(task_id)
        return info.status
    except Exception:
        return None


def render_tidy3d_panel(component: Any, api_key: Optional[str] = None) -> None:
    """
    Render Tidy3D simulation panel in Streamlit.
    """
    import streamlit as st

    st.subheader("Tidy3D FDTD Simulation")

    if not TIDY3D_AVAILABLE:
        st.warning("Tidy3D is not installed. Install with: pip install 'pixcell[simulate]'")
        return

    # API key input
    tidy3d_key = api_key or st.text_input(
        "Tidy3D API Key",
        type="password",
        help="Get your API key from https://tidy3d.simulation.cloud"
    )

    if not tidy3d_key:
        st.info("Enter your Tidy3D API key to enable simulation upload")
        return

    # Material selection
    material = st.selectbox(
        "Material Platform",
        options=list(MATERIAL_PRESETS.keys()),
        index=0
    )

    preset = MATERIAL_PRESETS[material]
    st.caption(preset["description"])

    # Custom material inputs
    custom_core_n = None
    custom_clad_n = None
    if material == "Custom":
        col1, col2 = st.columns(2)
        with col1:
            custom_core_n = st.number_input("Core n", value=2.5, min_value=1.0, max_value=5.0)
        with col2:
            custom_clad_n = st.number_input("Clad n", value=1.45, min_value=1.0, max_value=3.0)

    # Simulation parameters
    col1, col2 = st.columns(2)
    with col1:
        thickness_nm = st.number_input(
            "Thickness (nm)",
            value=preset["default_thickness"],
            min_value=50, max_value=2000
        )
    with col2:
        wavelength_um = st.number_input(
            "Wavelength (um)",
            value=1.55,
            min_value=0.4, max_value=4.0
        )

    # Layer selection
    st.markdown("**Layers to Include**")
    include_layer_1 = st.checkbox("Layer 1", value=True)
    include_layer_2 = st.checkbox("Layer 2", value=True)
    include_layer_3 = st.checkbox("Layer 3", value=False)

    layers = []
    if include_layer_1:
        layers.append((1, 0))
    if include_layer_2:
        layers.append((2, 0))
    if include_layer_3:
        layers.append((3, 0))

    # Upload button
    if st.button("Upload to Tidy3D", type="primary"):
        try:
            with st.spinner("Creating simulation..."):
                sim = create_simulation_from_component(
                    component=component,
                    layers=layers,
                    material=material,
                    thickness_nm=thickness_nm,
                    wavelength_um=wavelength_um,
                    api_key=tidy3d_key,
                    custom_core_n=custom_core_n,
                    custom_clad_n=custom_clad_n
                )

            with st.spinner("Uploading to cloud..."):
                task_id, web_url = upload_simulation(sim)

            st.success(f"Uploaded successfully!")
            st.markdown(f"[Open in Tidy3D Workbench]({web_url})")
            st.code(f"Task ID: {task_id}")

            # Estimate cost
            cost = estimate_simulation_cost(task_id)
            if cost:
                st.info(f"Estimated cost: {cost:.2f} FlexCredits")

        except Exception as e:
            st.error(f"Upload failed: {str(e)}")
