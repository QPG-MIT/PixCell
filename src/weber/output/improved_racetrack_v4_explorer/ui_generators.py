"""
UI Generators - Dynamic Streamlit UI generation for Weber explorers.

Generates:
- Collapsible sections for each slot category
- Dropdown menus to select component type
- Dynamic parameter sliders based on selected type
"""

import streamlit as st
from typing import Dict, Any, Tuple, List, Optional

# These will be set by the generated app
DEVICE_SLOTS = {}
GLOBAL_PARAMS = {}
COMPONENT_REGISTRY = {}


def init_ui_generators(slots: dict, global_params: dict, registry: dict):
    """Initialize the UI generators with slot and registry data."""
    global DEVICE_SLOTS, GLOBAL_PARAMS, COMPONENT_REGISTRY
    DEVICE_SLOTS = slots
    GLOBAL_PARAMS = global_params
    COMPONENT_REGISTRY = registry


def _get_spec_attr(spec, attr: str, default=None):
    """Get attribute from spec, handling both dict and dataclass."""
    if spec is None:
        return default
    if hasattr(spec, attr):
        return getattr(spec, attr)
    if isinstance(spec, dict):
        return spec.get(attr, default)
    return default


def _get_param_attr(param, attr: str, default=None):
    """Get attribute from parameter, handling both dict and dataclass."""
    if hasattr(param, attr):
        return getattr(param, attr)
    if isinstance(param, dict):
        return param.get(attr, default)
    return default


def get_default_params(comp_type: str) -> Dict[str, float]:
    """Get default parameters for a component type."""
    spec = COMPONENT_REGISTRY.get(comp_type)
    if not spec:
        return {}
    params = _get_spec_attr(spec, "parameters", [])
    return {_get_param_attr(p, "name"): _get_param_attr(p, "default_value") for p in params}


def render_slot_controls(
    slot_id: str,
    slot: dict,
    current_type: str,
    current_params: Dict[str, float]
) -> Tuple[str, Dict[str, float]]:
    """
    Render controls for a single slot (type dropdown + parameter sliders).
    All controls render to the SIDEBAR.
    """
    spec = COMPONENT_REGISTRY.get(current_type)

    # Component type dropdown
    type_options = slot.get("allowed_types", [current_type])
    display_names = []
    for t in type_options:
        reg_spec = COMPONENT_REGISTRY.get(t)
        display_names.append(_get_spec_attr(reg_spec, "display_name", t.replace("_", " ").title()))

    # Find current index
    if current_type in type_options:
        current_index = type_options.index(current_type)
    else:
        current_index = 0

    selected_display = st.sidebar.selectbox(
        "Component Type",
        options=display_names,
        index=current_index,
        key=f"{slot_id}_type_select",
        help=slot.get("description", "")
    )

    # Get selected type from display name
    selected_type = type_options[display_names.index(selected_display)]

    # If type changed, reset to defaults
    if selected_type != current_type:
        current_params = get_default_params(selected_type)

    # Dynamic parameter sliders
    new_params = {}
    selected_spec = COMPONENT_REGISTRY.get(selected_type)
    params_list = _get_spec_attr(selected_spec, "parameters", [])

    for param in params_list:
        # Get current value or default
        param_name = _get_param_attr(param, "name")
        param_default = _get_param_attr(param, "default_value", 1.0)
        param_min = _get_param_attr(param, "min_value", 0.1)
        param_max = _get_param_attr(param, "max_value", 10.0)
        param_step = _get_param_attr(param, "step", 0.1)
        param_label = _get_param_attr(param, "label", param_name)
        param_unit = _get_param_attr(param, "unit", "um")
        param_help = _get_param_attr(param, "help_text", "")

        default = current_params.get(param_name, param_default)
        # Clamp to valid range
        default = max(param_min, min(param_max, default))

        value = st.sidebar.slider(
            f"{param_label} ({param_unit})",
            min_value=float(param_min),
            max_value=float(param_max),
            value=float(default),
            step=float(param_step),
            key=f"{slot_id}_{param_name}_slider",
            help=param_help
        )
        new_params[param_name] = value

    return selected_type, new_params


def render_slots_by_category(category: str) -> Dict[str, Dict[str, Any]]:
    """
    Render all slots in a category in the sidebar.
    """
    config = {}
    slots_in_category = [
        (slot_id, slot) for slot_id, slot in DEVICE_SLOTS.items()
        if slot.get("category", "other") == category
    ]

    for slot_id, slot in slots_in_category:
        # Get current state from session state
        type_key = f"{slot_id}_current_type"
        params_key = f"{slot_id}_current_params"

        if type_key not in st.session_state:
            st.session_state[type_key] = slot.get("current_type", slot.get("allowed_types", ["unknown"])[0])
        if params_key not in st.session_state:
            # Use slot-specific defaults if available
            if slot.get("parameters"):
                st.session_state[params_key] = {
                    p["name"]: p["default_value"] for p in slot["parameters"]
                }
            else:
                st.session_state[params_key] = get_default_params(st.session_state[type_key])

        current_type = st.session_state[type_key]
        current_params = st.session_state[params_key]

        # Render slot label in sidebar
        st.sidebar.markdown(f"**{slot.get('display_name', slot_id)}**")

        # Render controls directly in sidebar
        selected_type, params = render_slot_controls(
            slot_id, slot, current_type, current_params
        )

        # Update session state
        st.session_state[type_key] = selected_type
        st.session_state[params_key] = params

        config[slot_id] = {
            "type": selected_type,
            "params": params
        }

        # Small separator between slots
        st.sidebar.markdown("---")

    return config


def render_global_params() -> Dict[str, float]:
    """
    Render global positioning parameters.
    """
    if not GLOBAL_PARAMS:
        return {}

    st.sidebar.subheader("Global Parameters")

    params = {}
    for param in GLOBAL_PARAMS:
        key = f"global_{param['name']}"

        if key not in st.session_state:
            st.session_state[key] = param.get("default_value", 0)

        value = st.sidebar.slider(
            param.get("label", param["name"]),
            min_value=float(param.get("min_value", 0)),
            max_value=float(param.get("max_value", 10)),
            value=float(st.session_state[key]),
            step=float(param.get("step", 0.1)),
            key=f"{key}_slider",
            help=param.get("help", "")
        )
        st.session_state[key] = value
        params[param["name"]] = value

    return params


def render_all_sections() -> Tuple[Dict[str, Dict[str, Any]], Dict[str, float]]:
    """
    Render entire sidebar with all categories and global params.
    """
    config = {}

    # Global positioning first
    global_params = render_global_params()

    if global_params:
        st.sidebar.divider()

    # Get all unique categories
    categories = set(slot.get("category", "other") for slot in DEVICE_SLOTS.values())

    for category in sorted(categories):
        st.sidebar.subheader(category.replace("_", " ").title())
        category_config = render_slots_by_category(category)
        config.update(category_config)

    return config, global_params


def get_config_summary(config: Dict[str, Dict[str, Any]]) -> Dict[str, str]:
    """
    Get a summary of current configuration (type for each slot).
    """
    return {
        slot_id: cfg["type"]
        for slot_id, cfg in config.items()
    }
