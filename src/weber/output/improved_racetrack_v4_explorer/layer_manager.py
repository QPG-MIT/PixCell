"""
Layer Manager - Layer definition and assignment UI for Weber explorers.

Provides:
- Layer definition UI (layer number, datatype, color)
- Slot-level and component-level layer assignment UI
- Layer summary display
- PDK (Process Design Kit) integration for foundry-specific layers

PDK Mode:
When a PDK is loaded (via built-in selection or PDF parsing), layers are
populated from the PDK definition with correct material properties for
downstream Tidy3D simulation.
"""

import streamlit as st
from typing import Dict, List, Tuple, Any, Optional
import json
import os
from pathlib import Path

# Try to import PDK module for advanced features
try:
    import sys
    # Go up to HOMI root: explorer -> output -> Weber -> HOMI
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
    from gg.pdk import (
        PDKDefinition,
        PDKLayer,
        PDKParser,
        load_builtin_pdk,
        list_builtin_pdks,
        LIGHTIUM_TFLN,
        HYPERLIGHT_ACTIVE,
        GENERIC_SI220,
    )
    PDK_AVAILABLE = True
except ImportError:
    PDK_AVAILABLE = False

# Default layer definitions (used when no PDK is loaded)
DEFAULT_LAYERS = {
    "Layer 1": {"layer": 1, "datatype": 0, "color": "#2E86AB"},
    "Layer 2": {"layer": 2, "datatype": 0, "color": "#F4A261"},
    "Layer 3": {"layer": 3, "datatype": 0, "color": "#E76F51"},
}

# Available builtin PDKs
BUILTIN_PDKS = {
    "None (Custom Layers)": None,
    "Lightium TFLN": "lightium_tfln",
    "HyperLight Active": "hyperlight_active",
    "Generic Si 220nm": "generic_si220",
}


def init_layer_state(slot_ids: List[str], component_map: Optional[Dict[str, List[str]]] = None):
    """Initialize layer-related session state.

    Args:
        slot_ids: List of slot IDs
        component_map: Optional dict mapping slot_id -> list of component_ids
    """
    if 'weber_layers' not in st.session_state:
        st.session_state.weber_layers = DEFAULT_LAYERS.copy()

    if 'weber_layer_assignments' not in st.session_state:
        # Default all slots to Layer 1
        st.session_state.weber_layer_assignments = {
            slot_id: "Layer 1" for slot_id in slot_ids
        }

    # Initialize component-level assignments
    if 'weber_component_layer_assignments' not in st.session_state:
        st.session_state.weber_component_layer_assignments = {}
        if component_map:
            for slot_id, comp_ids in component_map.items():
                slot_layer = st.session_state.weber_layer_assignments.get(slot_id, "Layer 1")
                for comp_id in comp_ids:
                    st.session_state.weber_component_layer_assignments[comp_id] = slot_layer

    # Initialize component mode toggles (False = slot-level, True = per-component)
    if 'weber_component_mode' not in st.session_state:
        st.session_state.weber_component_mode = {slot_id: False for slot_id in slot_ids}


def get_layer_tuple(layer_name: str) -> Tuple[int, int]:
    """Get (layer, datatype) tuple for a layer name."""
    layer_info = st.session_state.weber_layers.get(layer_name, {"layer": 1, "datatype": 0})
    return (layer_info["layer"], layer_info["datatype"])


def get_layer_for_component(component_id: str, slot_id: str) -> Tuple[int, int]:
    """Get layer tuple for a component, with slot-level fallback.

    Args:
        component_id: The component ID
        slot_id: The slot ID containing this component

    Returns:
        (layer, datatype) tuple
    """
    if st.session_state.weber_component_mode.get(slot_id, False):
        # Per-component mode: use component assignment
        layer_name = st.session_state.weber_component_layer_assignments.get(
            component_id,
            st.session_state.weber_layer_assignments.get(slot_id, "Layer 1")
        )
    else:
        # Slot-level mode: use slot assignment
        layer_name = st.session_state.weber_layer_assignments.get(slot_id, "Layer 1")

    return get_layer_tuple(layer_name)


def get_layer_color(layer_name: str) -> str:
    """Get color for a layer name."""
    layer_info = st.session_state.weber_layers.get(layer_name, {"color": "#888888"})
    return layer_info["color"]


def get_layer_colors_dict() -> Dict[Tuple[int, int], Dict[str, str]]:
    """Get layer colors in the format expected by visualization module."""
    colors = {}
    for layer_name, layer_info in st.session_state.weber_layers.items():
        layer_tuple = (layer_info["layer"], layer_info["datatype"])
        colors[layer_tuple] = {
            'face': layer_info['color'],
            'edge': layer_info['color'],
            'name': layer_name
        }
    return colors


def render_layer_definitions() -> None:
    """Render layer definition UI in sidebar."""
    st.sidebar.header("Layer Definitions")

    # Add new layer expander
    with st.sidebar.expander("Add New Layer", expanded=False):
        new_layer_name = st.text_input(
            "Layer Name",
            value=f"Layer {len(st.session_state.weber_layers) + 1}",
            key="new_layer_name"
        )
        col1, col2 = st.columns(2)
        with col1:
            new_layer_num = st.number_input(
                "Layer #", min_value=1, max_value=255,
                value=len(st.session_state.weber_layers) + 1,
                key="new_layer_num"
            )
        with col2:
            new_datatype = st.number_input(
                "Datatype", min_value=0, max_value=255, value=0,
                key="new_layer_datatype"
            )
        new_color = st.color_picker("Color", value="#9B59B6", key="new_layer_color")

        if st.button("Add Layer", key="add_layer_btn"):
            if new_layer_name and new_layer_name not in st.session_state.weber_layers:
                st.session_state.weber_layers[new_layer_name] = {
                    "layer": new_layer_num,
                    "datatype": new_datatype,
                    "color": new_color
                }
                st.rerun()
            elif new_layer_name in st.session_state.weber_layers:
                st.warning("Layer name already exists!")

    # Display existing layers
    st.sidebar.markdown("---")
    st.sidebar.subheader("Defined Layers")

    layers_to_remove = []
    for layer_name, layer_info in st.session_state.weber_layers.items():
        col1, col2, col3 = st.sidebar.columns([2, 1, 1])
        with col1:
            st.markdown(f"**{layer_name}**")
            st.caption(f"({layer_info['layer']}, {layer_info['datatype']})")
        with col2:
            new_color = st.color_picker(
                "c",
                value=layer_info['color'],
                key=f"color_{layer_name}",
                label_visibility="collapsed"
            )
            if new_color != layer_info['color']:
                st.session_state.weber_layers[layer_name]['color'] = new_color
        with col3:
            if len(st.session_state.weber_layers) > 1:
                if st.button("X", key=f"del_{layer_name}"):
                    layers_to_remove.append(layer_name)

    # Process layer deletions
    for layer_name in layers_to_remove:
        del st.session_state.weber_layers[layer_name]
        # Reassign slots/components to first available layer
        first_layer = list(st.session_state.weber_layers.keys())[0]
        for slot_id, assigned in st.session_state.weber_layer_assignments.items():
            if assigned == layer_name:
                st.session_state.weber_layer_assignments[slot_id] = first_layer
        # Also reassign component-level assignments
        for comp_id, assigned in st.session_state.weber_component_layer_assignments.items():
            if assigned == layer_name:
                st.session_state.weber_component_layer_assignments[comp_id] = first_layer
        st.rerun()


def render_layer_assignments(slots: Dict[str, Dict[str, Any]]) -> None:
    """Render layer assignment UI in sidebar with per-component support.

    Args:
        slots: Dictionary of slot definitions (DEVICE_SLOTS)
    """
    st.sidebar.markdown("---")
    st.sidebar.header("Layer Assignments")

    layer_names = list(st.session_state.weber_layers.keys())

    for slot_id, slot in slots.items():
        component_ids = slot.get("component_ids", [slot_id])
        display_name = slot.get("display_name", slot_id.replace("_", " ").title())
        has_multiple_components = len(component_ids) > 1

        # Determine expander label
        if has_multiple_components:
            expander_label = f"{display_name} ({len(component_ids)} components)"
        else:
            expander_label = display_name

        with st.sidebar.expander(expander_label, expanded=False):
            # Get current slot-level assignment
            current_slot_assignment = st.session_state.weber_layer_assignments.get(slot_id, layer_names[0])
            if current_slot_assignment not in layer_names:
                current_slot_assignment = layer_names[0]
                st.session_state.weber_layer_assignments[slot_id] = current_slot_assignment

            # Mode toggle (only show if multiple components)
            if has_multiple_components:
                component_mode = st.checkbox(
                    "Per-component layers",
                    value=st.session_state.weber_component_mode.get(slot_id, False),
                    key=f"component_mode_{slot_id}",
                    help="Enable to assign different layers to each component"
                )
                st.session_state.weber_component_mode[slot_id] = component_mode
            else:
                component_mode = False
                st.session_state.weber_component_mode[slot_id] = False

            if not component_mode:
                # Slot-level dropdown
                new_assignment = st.selectbox(
                    "Layer",
                    options=layer_names,
                    index=layer_names.index(current_slot_assignment),
                    key=f"layer_assign_{slot_id}",
                    label_visibility="collapsed" if has_multiple_components else "visible"
                )
                st.session_state.weber_layer_assignments[slot_id] = new_assignment

                # Sync button to apply slot layer to all components
                if has_multiple_components:
                    if st.button("Sync to all components", key=f"sync_{slot_id}"):
                        for comp_id in component_ids:
                            st.session_state.weber_component_layer_assignments[comp_id] = new_assignment
                        st.toast(f"Applied {new_assignment} to all components")
            else:
                # Per-component dropdowns
                st.caption("Assign each component:")
                for comp_id in component_ids:
                    # Get current component assignment, defaulting to slot layer
                    current_comp_layer = st.session_state.weber_component_layer_assignments.get(
                        comp_id, current_slot_assignment
                    )
                    if current_comp_layer not in layer_names:
                        current_comp_layer = layer_names[0]

                    # Display name for component
                    comp_display = comp_id.replace("_", " ").title()

                    new_comp_assignment = st.selectbox(
                        comp_display,
                        options=layer_names,
                        index=layer_names.index(current_comp_layer),
                        key=f"layer_assign_{slot_id}_{comp_id}"
                    )
                    st.session_state.weber_component_layer_assignments[comp_id] = new_comp_assignment


def render_layer_summary() -> None:
    """Render layer assignment summary with component details."""
    st.subheader("Layer Summary")

    # Collect all assignments (both slot-level and component-level)
    layer_items: Dict[str, List[str]] = {layer_name: [] for layer_name in st.session_state.weber_layers.keys()}

    # Add slot-level assignments (for slots not in component mode)
    for slot_id, layer_name in st.session_state.weber_layer_assignments.items():
        if not st.session_state.weber_component_mode.get(slot_id, False):
            if layer_name in layer_items:
                display_name = slot_id.replace("_", " ").title()
                layer_items[layer_name].append(display_name)

    # Add component-level assignments (for slots in component mode)
    for comp_id, layer_name in st.session_state.weber_component_layer_assignments.items():
        # Check if this component's slot is in component mode
        # We need to find which slot this component belongs to
        slot_in_component_mode = False
        for slot_id, mode in st.session_state.weber_component_mode.items():
            if mode:
                slot_in_component_mode = True
                break

        # Only add component-level items if they're in component mode
        if slot_in_component_mode and layer_name in layer_items:
            display_name = comp_id.replace("_", " ").title()
            if display_name not in layer_items[layer_name]:
                layer_items[layer_name].append(f"{display_name} (component)")

    # Render summary
    for layer_name, layer_info in st.session_state.weber_layers.items():
        items = layer_items.get(layer_name, [])
        if items:
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"**{layer_name}** ({layer_info['layer']},{layer_info['datatype']})")
            with col2:
                st.markdown(f"<span style='color:{layer_info['color']}; font-size: 20px;'>●</span>", unsafe_allow_html=True)

            for item in items:
                st.caption(f"  - {item}")


def export_layer_config() -> str:
    """Export layer configuration as JSON string including component-level data."""
    config = {
        "layers": st.session_state.weber_layers,
        "slot_assignments": st.session_state.weber_layer_assignments,
        "component_assignments": st.session_state.weber_component_layer_assignments,
        "component_mode": st.session_state.weber_component_mode,
    }
    return json.dumps(config, indent=2)


def import_layer_config(json_str: str) -> bool:
    """Import layer configuration from JSON string."""
    try:
        config = json.loads(json_str)
        if "layers" in config:
            st.session_state.weber_layers = config["layers"]

        # Handle slot assignments (support old "assignments" key for backward compat)
        if "slot_assignments" in config:
            st.session_state.weber_layer_assignments = config["slot_assignments"]
        elif "assignments" in config:
            st.session_state.weber_layer_assignments = config["assignments"]

        # Handle component-level data
        if "component_assignments" in config:
            st.session_state.weber_component_layer_assignments = config["component_assignments"]
        if "component_mode" in config:
            st.session_state.weber_component_mode = config["component_mode"]

        # Handle PDK data
        if "pdk" in config and PDK_AVAILABLE:
            pdk_data = config["pdk"]
            if pdk_data.get("definition"):
                st.session_state.weber_pdk = PDKDefinition.from_dict(pdk_data["definition"])
            st.session_state.weber_pdk_name = pdk_data.get("name", "")

        return True
    except Exception:
        return False


# =============================================================================
# PDK Support Functions
# =============================================================================

def is_pdk_mode() -> bool:
    """Check if PDK mode is active."""
    return PDK_AVAILABLE and st.session_state.get("weber_pdk") is not None


def get_pdk() -> Optional["PDKDefinition"]:
    """Get the currently loaded PDK definition."""
    if not PDK_AVAILABLE:
        return None
    return st.session_state.get("weber_pdk")


def init_pdk_layer_state(pdk: "PDKDefinition", slot_ids: List[str]) -> None:
    """
    Initialize layer state from a PDK definition.

    Replaces default layers with PDK-defined layers and resets assignments.

    Args:
        pdk: PDKDefinition to use
        slot_ids: List of slot IDs for assignment initialization
    """
    if not PDK_AVAILABLE:
        return

    st.session_state.weber_pdk = pdk
    st.session_state.weber_pdk_name = pdk.name

    # Build layer definitions from PDK
    st.session_state.weber_layers = {}
    for layer in pdk.layers.values():
        st.session_state.weber_layers[layer.name] = {
            "layer": layer.gds_number,
            "datatype": layer.datatype,
            "color": layer.color,
            "pdk_layer": layer.to_dict(),  # Store full PDK info
        }

    # Reset assignments to first core layer
    core_layers = pdk.get_core_layers()
    default_layer = core_layers[0].name if core_layers else list(pdk.layers.keys())[0]

    st.session_state.weber_layer_assignments = {
        slot_id: default_layer for slot_id in slot_ids
    }
    st.session_state.weber_component_layer_assignments = {}
    st.session_state.weber_component_mode = {slot_id: False for slot_id in slot_ids}


def render_pdk_configuration(slot_ids: List[str]) -> None:
    """
    Render PDK configuration UI in sidebar.

    Allows users to:
    - Select from builtin PDKs
    - Upload custom PDK PDF
    - View PDK summary

    Args:
        slot_ids: List of slot IDs for reinitialization after PDK change
    """
    if not PDK_AVAILABLE:
        st.sidebar.warning("PDK module not available. Using default layers.")
        return

    with st.sidebar.expander("PDK Configuration", expanded=False):
        current_pdk_name = st.session_state.get("weber_pdk_name", "None (Custom Layers)")

        # PDK selection dropdown
        pdk_options = list(BUILTIN_PDKS.keys())
        current_index = 0
        for i, name in enumerate(pdk_options):
            if name == current_pdk_name or BUILTIN_PDKS.get(name) == current_pdk_name:
                current_index = i
                break

        selected_pdk = st.selectbox(
            "Select PDK",
            options=pdk_options,
            index=current_index,
            key="pdk_selector",
            help="Choose a foundry PDK to use PDK-defined layers"
        )

        # Handle PDK change
        selected_pdk_id = BUILTIN_PDKS.get(selected_pdk)
        if selected_pdk_id and selected_pdk_id != st.session_state.get("weber_pdk_name"):
            if st.button("Load PDK", key="load_pdk_btn"):
                try:
                    pdk = load_builtin_pdk(selected_pdk_id)
                    init_pdk_layer_state(pdk, slot_ids)
                    st.success(f"Loaded {pdk.name}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to load PDK: {e}")

        elif selected_pdk == "None (Custom Layers)" and is_pdk_mode():
            if st.button("Clear PDK", key="clear_pdk_btn"):
                st.session_state.weber_pdk = None
                st.session_state.weber_pdk_name = None
                st.session_state.weber_layers = DEFAULT_LAYERS.copy()
                st.session_state.weber_layer_assignments = {
                    slot_id: "Layer 1" for slot_id in slot_ids
                }
                st.rerun()

        # Upload custom PDK
        st.markdown("---")
        st.caption("Or upload custom PDK PDF:")
        uploaded_pdf = st.file_uploader(
            "Upload PDK PDF",
            type=["pdf"],
            key="pdk_pdf_upload",
            help="Upload a foundry PDK document to parse layer definitions"
        )

        if uploaded_pdf:
            pdk_name_input = st.text_input(
                "PDK Name",
                value=uploaded_pdf.name.replace(".pdf", "").replace("_", " ").title(),
                key="custom_pdk_name"
            )

            if st.button("Parse PDK", key="parse_pdk_btn"):
                with st.spinner("Parsing PDK document..."):
                    try:
                        # Save uploaded file temporarily
                        import tempfile
                        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                            tmp.write(uploaded_pdf.read())
                            tmp_path = tmp.name

                        # Parse the PDF
                        import asyncio
                        parser = PDKParser()
                        pdk = asyncio.run(parser.parse_pdf(tmp_path, pdk_name_input))

                        # Clean up
                        os.unlink(tmp_path)

                        # Initialize state
                        init_pdk_layer_state(pdk, slot_ids)

                        st.success(f"Parsed {pdk.name} ({len(pdk.layers)} layers, {len(pdk.materials)} materials)")
                        st.rerun()

                    except Exception as e:
                        st.error(f"Failed to parse PDK: {e}")

        # Show current PDK summary
        if is_pdk_mode():
            pdk = get_pdk()
            st.markdown("---")
            st.caption(f"**Active PDK:** {pdk.name}")
            st.caption(f"Foundry: {pdk.foundry}")
            st.caption(f"Layers: {len(pdk.layers)} | Materials: {len(pdk.materials)}")


def render_pdk_layer_palette() -> None:
    """
    Render PDK layer palette grouped by purpose.

    Shows layers with their material properties and colors.
    """
    if not is_pdk_mode():
        return

    pdk = get_pdk()
    st.sidebar.markdown("---")
    st.sidebar.subheader("PDK Layers")

    # Group layers by purpose
    purposes = {}
    for layer in pdk.layers.values():
        purpose = layer.purpose
        if purpose not in purposes:
            purposes[purpose] = []
        purposes[purpose].append(layer)

    # Purpose display order
    purpose_order = ["core", "slab", "metal", "via", "heater", "pad", "marker", "cladding", "trench"]

    for purpose in purpose_order:
        layers = purposes.get(purpose, [])
        if not layers:
            continue

        st.sidebar.caption(f"**{purpose.title()} Layers:**")

        for layer in layers:
            col1, col2 = st.sidebar.columns([3, 1])
            with col1:
                # Layer name with GDS info
                label = f"{layer.name}"
                tooltip_parts = [f"GDS: ({layer.gds_number}, {layer.datatype})"]

                if layer.thickness_nm:
                    tooltip_parts.append(f"Thickness: {layer.thickness_nm}nm")
                if layer.etch_depth_nm:
                    tooltip_parts.append(f"Etch: {layer.etch_depth_nm}nm")
                if layer.material_name:
                    tooltip_parts.append(f"Material: {layer.material_name}")
                    material = pdk.get_material(layer.material_name)
                    if material:
                        if material.is_anisotropic:
                            tooltip_parts.append(f"n_o={material.n_ordinary:.3f}, n_e={material.n_extraordinary:.3f}")
                        else:
                            tooltip_parts.append(f"n={material.n_ordinary:.3f}")

                tooltip = " | ".join(tooltip_parts)
                st.markdown(f"<span title='{tooltip}'>{label}</span>", unsafe_allow_html=True)
                st.caption(f"GDS {layer.gds_number}")

            with col2:
                st.markdown(
                    f"<span style='color:{layer.color}; font-size: 20px;'>●</span>",
                    unsafe_allow_html=True
                )


def render_pdk_layer_assignments(slots: Dict[str, Dict[str, Any]]) -> None:
    """
    Render PDK-aware layer assignment UI.

    When PDK is loaded, shows PDK layers grouped by purpose.
    Also displays material properties for the selected layer.

    Args:
        slots: Dictionary of slot definitions (DEVICE_SLOTS)
    """
    if not is_pdk_mode():
        # Fall back to default
        render_layer_assignments(slots)
        return

    pdk = get_pdk()
    st.sidebar.markdown("---")
    st.sidebar.header("Layer Assignments")

    # Get layer names, grouped by purpose for display
    layer_names = list(pdk.layers.keys())

    for slot_id, slot in slots.items():
        component_ids = slot.get("component_ids", [slot_id])
        display_name = slot.get("display_name", slot_id.replace("_", " ").title())

        with st.sidebar.expander(display_name, expanded=False):
            # Get current assignment
            current_assignment = st.session_state.weber_layer_assignments.get(slot_id, layer_names[0])
            if current_assignment not in layer_names:
                current_assignment = layer_names[0]
                st.session_state.weber_layer_assignments[slot_id] = current_assignment

            # Layer dropdown
            new_assignment = st.selectbox(
                "PDK Layer",
                options=layer_names,
                index=layer_names.index(current_assignment),
                key=f"pdk_layer_assign_{slot_id}"
            )
            st.session_state.weber_layer_assignments[slot_id] = new_assignment

            # Show layer properties
            layer = pdk.get_layer(new_assignment)
            if layer:
                props = []
                if layer.thickness_nm:
                    props.append(f"Thickness: {layer.thickness_nm}nm")
                if layer.etch_depth_nm:
                    props.append(f"Etch depth: {layer.etch_depth_nm}nm")
                if layer.sidewall_angle_deg:
                    props.append(f"Sidewall: {layer.sidewall_angle_deg}°")

                if props:
                    st.caption(" | ".join(props))

                # Material info
                if layer.material_name:
                    material = pdk.get_material(layer.material_name)
                    if material:
                        if material.is_anisotropic:
                            st.caption(f"Material: {material.name} (n_o={material.n_ordinary:.3f}, n_e={material.n_extraordinary:.3f})")
                        else:
                            st.caption(f"Material: {material.name} (n={material.n_ordinary:.3f})")


def export_pdk_layer_config() -> str:
    """
    Export layer configuration with full PDK data.

    Returns JSON string including PDK definition for downstream simulation.
    """
    config = {
        "layers": st.session_state.weber_layers,
        "slot_assignments": st.session_state.weber_layer_assignments,
        "component_assignments": st.session_state.weber_component_layer_assignments,
        "component_mode": st.session_state.weber_component_mode,
    }

    # Include PDK data if available
    if is_pdk_mode():
        pdk = get_pdk()
        config["pdk"] = {
            "name": pdk.name,
            "definition": pdk.to_dict(),
        }

    return json.dumps(config, indent=2)


def get_simulation_layer_info(slot_id: str) -> Dict[str, Any]:
    """
    Get simulation-ready layer information for a slot.

    Returns material properties, thickness, etc. for Tidy3D simulation.

    Args:
        slot_id: Slot ID to get info for

    Returns:
        Dictionary with simulation parameters
    """
    if not is_pdk_mode():
        # Return basic info from default layers
        layer_name = st.session_state.weber_layer_assignments.get(slot_id, "Layer 1")
        layer_info = st.session_state.weber_layers.get(layer_name, {})
        return {
            "layer_name": layer_name,
            "gds_layer": layer_info.get("layer", 1),
            "gds_datatype": layer_info.get("datatype", 0),
            "pdk_mode": False,
        }

    pdk = get_pdk()
    layer_name = st.session_state.weber_layer_assignments.get(slot_id)
    if not layer_name:
        return {"error": f"No layer assigned to slot {slot_id}"}

    layer = pdk.get_layer(layer_name)
    if not layer:
        return {"error": f"Layer {layer_name} not found in PDK"}

    info = {
        "pdk_mode": True,
        "pdk_name": pdk.name,
        "layer_name": layer.name,
        "gds_layer": layer.gds_number,
        "gds_datatype": layer.datatype,
        "purpose": layer.purpose,
    }

    # Add geometry info
    if layer.thickness_nm:
        info["thickness_nm"] = layer.thickness_nm
        info["thickness_um"] = layer.thickness_nm / 1000
    if layer.etch_depth_nm:
        info["etch_depth_nm"] = layer.etch_depth_nm
    if layer.sidewall_angle_deg:
        info["sidewall_angle_deg"] = layer.sidewall_angle_deg

    # Add material info
    if layer.material_name:
        material = pdk.get_material(layer.material_name)
        if material:
            info["material"] = {
                "name": material.name,
                "n_ordinary": material.n_ordinary,
                "is_anisotropic": material.is_anisotropic,
            }
            if material.is_anisotropic:
                info["material"]["n_extraordinary"] = material.n_extraordinary
                info["material"]["crystal_cut"] = material.crystal_cut
            if material.clad_n:
                info["material"]["clad_n"] = material.clad_n

    return info
