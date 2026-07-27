"""
Simulation UI Components for Step 8.

Provides Streamlit UI components for Tidy3D FDTD simulation configuration
and cloud upload functionality.
"""

import streamlit as st
from typing import Dict, Any, Tuple, List, Optional

from .flex_integration import (
    is_tidy3d_available,
    get_material_presets,
    get_simulation_info,
    create_and_upload_simulation,
    get_task_status,
    get_workbench_url,
    validate_api_key
)


# =============================================================================
# SESSION STATE INITIALIZATION
# =============================================================================

def init_simulation_state():
    """Initialize session state for simulation."""
    defaults = {
        "sim_api_key": "",
        "sim_api_key_valid": False,
        "sim_material": "Silicon (SOI)",
        "sim_thickness_nm": 220,
        "sim_wavelength_um": 1.55,
        "sim_layers": [(1, 0)],
        "sim_custom_core_n": 2.5,
        "sim_custom_clad_n": 1.45,
        "sim_task_history": [],
        "sim_last_result": None,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


# =============================================================================
# UI COMPONENTS
# =============================================================================

def render_api_key_input() -> Optional[str]:
    """
    Render API key input field.

    Returns:
        API key string if valid, None otherwise
    """
    st.sidebar.markdown("### Tidy3D API Key")

    api_key = st.sidebar.text_input(
        "API Key",
        value=st.session_state.sim_api_key,
        type="password",
        help="Your Tidy3D API key for cloud simulations"
    )

    # Update session state
    if api_key != st.session_state.sim_api_key:
        st.session_state.sim_api_key = api_key
        st.session_state.sim_api_key_valid = False

    # Validate button
    col1, col2 = st.sidebar.columns(2)

    with col1:
        if st.button("Validate", key="validate_api_key"):
            if api_key:
                with st.spinner("Validating..."):
                    is_valid = validate_api_key(api_key)
                    st.session_state.sim_api_key_valid = is_valid
                    if is_valid:
                        st.success("Valid!")
                    else:
                        st.error("Invalid key")
            else:
                st.warning("Enter a key")

    with col2:
        st.link_button(
            "Get Key",
            "https://tidy3d.simulation.cloud/account",
            help="Get your API key from Tidy3D"
        )

    # Show validation status
    if st.session_state.sim_api_key_valid:
        st.sidebar.success("API key validated")

    return api_key if api_key else None


def render_material_selector() -> Tuple[str, Dict[str, Any]]:
    """
    Render material platform selector.

    Returns:
        Tuple of (material_name, material_info)
    """
    st.sidebar.markdown("### Material Platform")

    presets = get_material_presets()
    material_names = list(presets.keys())

    # Find current index
    current_idx = 0
    if st.session_state.sim_material in material_names:
        current_idx = material_names.index(st.session_state.sim_material)

    selected = st.sidebar.selectbox(
        "Material",
        material_names,
        index=current_idx,
        key="material_selector"
    )

    # Update session state
    st.session_state.sim_material = selected

    # Get preset info
    preset_info = presets.get(selected, {})

    # Show description
    if "description" in preset_info:
        st.sidebar.caption(preset_info["description"])

    # Custom material inputs
    if selected == "Custom":
        st.sidebar.markdown("**Custom Indices**")

        core_n = st.sidebar.number_input(
            "Core n",
            min_value=1.0,
            max_value=5.0,
            value=st.session_state.sim_custom_core_n,
            step=0.01,
            format="%.3f"
        )
        st.session_state.sim_custom_core_n = core_n

        clad_n = st.sidebar.number_input(
            "Cladding n",
            min_value=1.0,
            max_value=3.0,
            value=st.session_state.sim_custom_clad_n,
            step=0.01,
            format="%.3f"
        )
        st.session_state.sim_custom_clad_n = clad_n

        preset_info["core_n"] = core_n
        preset_info["clad_n"] = clad_n

    return selected, preset_info


def render_simulation_params(available_layers: List[Tuple[int, int]]) -> Dict[str, Any]:
    """
    Render simulation parameters.

    Args:
        available_layers: List of (layer, datatype) tuples available in component

    Returns:
        Dict with simulation configuration
    """
    st.sidebar.markdown("### Simulation Parameters")

    # Thickness
    presets = get_material_presets()
    current_material = st.session_state.sim_material
    default_thickness = presets.get(current_material, {}).get("default_thickness_nm", 220)

    thickness = st.sidebar.number_input(
        "Thickness (nm)",
        min_value=50,
        max_value=2000,
        value=st.session_state.sim_thickness_nm or default_thickness,
        step=10
    )
    st.session_state.sim_thickness_nm = thickness

    # Wavelength
    wavelength = st.sidebar.number_input(
        "Wavelength (um)",
        min_value=0.4,
        max_value=10.0,
        value=st.session_state.sim_wavelength_um,
        step=0.01,
        format="%.3f"
    )
    st.session_state.sim_wavelength_um = wavelength

    # Layer selection
    st.sidebar.markdown("### Layers to Include")

    selected_layers = []
    for layer, datatype in available_layers:
        layer_key = f"layer_{layer}_{datatype}"
        is_selected = st.sidebar.checkbox(
            f"Layer {layer}/{datatype}",
            value=(layer, datatype) in st.session_state.sim_layers,
            key=layer_key
        )
        if is_selected:
            selected_layers.append((layer, datatype))

    # Ensure at least one layer
    if not selected_layers and available_layers:
        selected_layers = [available_layers[0]]

    st.session_state.sim_layers = selected_layers

    return {
        "material": st.session_state.sim_material,
        "thickness_nm": thickness,
        "wavelength_um": wavelength,
        "layers": selected_layers,
        "custom_core_n": st.session_state.sim_custom_core_n if current_material == "Custom" else None,
        "custom_clad_n": st.session_state.sim_custom_clad_n if current_material == "Custom" else None,
    }


def render_simulation_info(component: Any, config: Dict[str, Any]):
    """
    Render simulation information panel.

    Args:
        component: GDSFactory Component
        config: Simulation configuration
    """
    st.markdown("### Simulation Info")

    sim_info = get_simulation_info(
        component,
        config.get("layers", [(1, 0)]),
        config.get("thickness_nm", 220),
        config.get("wavelength_um", 1.55)
    )

    if sim_info:
        col1, col2, col3 = st.columns(3)

        with col1:
            domain = sim_info.get("domain_size_um", (0, 0, 0))
            st.metric("Domain Size", f"{domain[0]}x{domain[1]}x{domain[2]} um")

        with col2:
            st.metric("Grid Resolution", f"{sim_info.get('grid_resolution', 12)} pts/lambda")

        with col3:
            st.metric("Run Time", f"{sim_info.get('run_time_ps', 1.0)} ps")

        # Additional info
        with st.expander("More Details"):
            st.write(f"**Wavelength:** {sim_info.get('wavelength_um', 1.55)} um")
            st.write(f"**Thickness:** {sim_info.get('thickness_um', 0.22)} um")
            st.write(f"**Layers:** {sim_info.get('layers', [])}")
            st.write(f"**Mode Monitors:** {sim_info.get('num_modes', 2)} modes")


def render_upload_section(
    component: Any,
    config: Dict[str, Any],
    api_key: str,
    task_name: str = "Device"
) -> Optional[Dict[str, Any]]:
    """
    Render upload button and results.

    Args:
        component: GDSFactory Component
        config: Simulation configuration
        api_key: Tidy3D API key
        task_name: Name for the simulation task

    Returns:
        Upload result dict if successful, None otherwise
    """
    st.markdown("### Upload to Tidy3D Cloud")

    # Validation checks
    can_upload = True
    warnings = []

    if not api_key:
        warnings.append("API key required")
        can_upload = False

    if not config.get("layers"):
        warnings.append("Select at least one layer")
        can_upload = False

    if component is None:
        warnings.append("No component available")
        can_upload = False

    # Show warnings
    for warning in warnings:
        st.warning(warning)

    # Upload button
    col1, col2 = st.columns([2, 1])

    with col1:
        upload_clicked = st.button(
            "Upload Simulation",
            disabled=not can_upload,
            type="primary",
            use_container_width=True
        )

    with col2:
        task_name_input = st.text_input(
            "Task Name",
            value=task_name,
            max_chars=50,
            label_visibility="collapsed",
            placeholder="Task name"
        )

    result = None

    if upload_clicked and can_upload:
        with st.spinner("Creating and uploading simulation..."):
            try:
                # Add task name to config
                full_config = {**config, "task_name": task_name_input}

                result = create_and_upload_simulation(
                    component,
                    full_config,
                    api_key
                )

                # Store in session state
                st.session_state.sim_last_result = result

                # Add to history
                history_entry = {
                    "task_id": result.get("task_id"),
                    "task_name": task_name_input,
                    "web_url": result.get("web_url"),
                    "estimated_cost": result.get("estimated_cost"),
                    "config": config.copy()
                }
                st.session_state.sim_task_history.insert(0, history_entry)

                # Keep only last 10 entries
                st.session_state.sim_task_history = st.session_state.sim_task_history[:10]

                st.success("Simulation uploaded successfully!")

            except Exception as e:
                st.error(f"Upload failed: {str(e)}")
                return None

    # Show last result
    if st.session_state.sim_last_result:
        result = st.session_state.sim_last_result

        st.markdown("---")
        st.markdown("#### Last Upload Result")

        col1, col2 = st.columns(2)

        with col1:
            st.write(f"**Task ID:** `{result.get('task_id', 'N/A')}`")

            cost = result.get("estimated_cost")
            if cost is not None:
                st.write(f"**Estimated Cost:** {cost:.2f} FlexCredits")
            else:
                st.write("**Estimated Cost:** N/A")

        with col2:
            web_url = result.get("web_url", "")
            if web_url:
                st.link_button(
                    "Open in Tidy3D Workbench",
                    web_url,
                    type="primary",
                    use_container_width=True
                )

    return result


def render_task_history():
    """Render previous simulation task history."""
    history = st.session_state.get("sim_task_history", [])

    if not history:
        st.info("No previous simulations in this session")
        return

    st.markdown("### Task History")

    for i, entry in enumerate(history):
        task_id = entry.get("task_id", "unknown")
        task_name = entry.get("task_name", "Device")
        web_url = entry.get("web_url", "")
        cost = entry.get("estimated_cost")

        with st.expander(f"{task_name} ({task_id[:8]}...)", expanded=(i == 0)):
            col1, col2, col3 = st.columns([2, 1, 1])

            with col1:
                st.write(f"**Task ID:** `{task_id}`")

                # Try to get current status
                status = get_task_status(task_id)
                if status:
                    status_color = {
                        "success": "green",
                        "running": "blue",
                        "queued": "orange",
                        "error": "red"
                    }.get(status, "gray")
                    st.markdown(f"**Status:** :{status_color}[{status}]")

            with col2:
                if cost is not None:
                    st.write(f"**Cost:** {cost:.2f} FC")

            with col3:
                if web_url:
                    st.link_button("View", web_url, use_container_width=True)

            # Show config details
            config = entry.get("config", {})
            if config:
                st.caption(
                    f"Material: {config.get('material', 'N/A')} | "
                    f"Thickness: {config.get('thickness_nm', 'N/A')} nm | "
                    f"Wavelength: {config.get('wavelength_um', 'N/A')} um"
                )


def render_tidy3d_unavailable():
    """Render message when Tidy3D is not available."""
    st.warning("Tidy3D FDTD simulation is not available.")

    st.markdown("""
    ### Installation Required

    To enable FDTD simulation, install Tidy3D and gdstk:

    ```bash
    pip install 'pixcell[simulate]'
    ```

    After installation, restart the application.
    """)

    st.link_button(
        "Tidy3D Documentation",
        "https://docs.flexcompute.com/projects/tidy3d/en/latest/",
        type="secondary"
    )


def get_component_layers(component: Any) -> List[Tuple[int, int]]:
    """
    Get list of layers used in a GDSFactory component.

    Args:
        component: GDSFactory Component

    Returns:
        List of (layer, datatype) tuples
    """
    layers = set()

    try:
        # Try to get layers from component
        if hasattr(component, 'get_layers'):
            for layer in component.get_layers():
                if isinstance(layer, tuple):
                    layers.add(layer)
                else:
                    layers.add((layer, 0))
        elif hasattr(component, 'layers'):
            for layer in component.layers:
                if isinstance(layer, tuple):
                    layers.add(layer)
                else:
                    layers.add((layer, 0))
        else:
            # Default to common layers
            layers = {(1, 0), (2, 0)}
    except Exception:
        layers = {(1, 0)}

    return sorted(list(layers))
