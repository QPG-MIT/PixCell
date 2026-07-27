"""
Layer Manager - Layer definition and assignment UI for Weber explorers.

Provides:
- Layer definition UI (layer number, datatype, color)
- Slot-level and component-level layer assignment UI
- Layer summary display
"""

import streamlit as st
from typing import Dict, List, Tuple, Any, Optional
import json


# Default layer definitions
DEFAULT_LAYERS = {
    "Layer 1": {"layer": 1, "datatype": 0, "color": "#2E86AB"},
    "Layer 2": {"layer": 2, "datatype": 0, "color": "#F4A261"},
    "Layer 3": {"layer": 3, "datatype": 0, "color": "#E76F51"},
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

        return True
    except Exception:
        return False
