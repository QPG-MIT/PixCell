"""
UI Generators - Dynamic Streamlit UI generation for Weber explorers.

Generates:
- Parameter sliders for tunable values
- Quick presets buttons
- Custom primitives sidebar
- Interactive canvas controls
"""

import streamlit as st
from typing import Dict, Any, Tuple, List, Optional

# These will be set by the generated app
DEVICE_SLOTS = {}
GLOBAL_PARAMS = []  # list of {name,label,min_value,max_value,default_value,step} dicts
TUNABLE_PARAMS = []

# Primitive types for custom primitives
PRIMITIVE_TYPES = {
    "rectangle": {"params": ["width", "height"], "defaults": {"width": 0.5, "height": 0.3}},
    "circle": {"params": ["radius"], "defaults": {"radius": 0.2}},
    "ellipse": {"params": ["rx", "ry"], "defaults": {"rx": 0.3, "ry": 0.2}},
    "triangle": {"params": ["x", "y"], "defaults": {"x": 0.3, "y": 0.3}},
    "straight": {"params": ["length", "width"], "defaults": {"length": 1.0, "width": 0.3}},
}


def init_ui_generators(slots: dict, global_params: dict, tunable_params: list):
    """Initialize the UI generators with slot and parameter data."""
    global DEVICE_SLOTS, GLOBAL_PARAMS, TUNABLE_PARAMS
    DEVICE_SLOTS = slots
    GLOBAL_PARAMS = global_params
    TUNABLE_PARAMS = tunable_params


def init_custom_primitives_state():
    """Initialize session state for custom primitives."""
    if "custom_primitives" not in st.session_state:
        st.session_state.custom_primitives = []


def _suggest_slider_range(value: float, name: str) -> Tuple[float, float, float]:
    """Suggest min, max, step for a parameter value."""
    if value == 0:
        return (-1.0, 1.0, 0.1)

    # Handle different scales
    abs_val = abs(value)

    if abs_val < 0.1:
        step = 0.01
        min_val = 0.0
        max_val = value * 5
    elif abs_val < 1:
        step = 0.05
        min_val = 0.0
        max_val = value * 3
    elif abs_val < 10:
        step = 0.1
        min_val = value * 0.2
        max_val = value * 3
    elif abs_val < 100:
        step = 1.0
        min_val = value * 0.2
        max_val = value * 3
    else:
        step = 10.0
        min_val = value * 0.2
        max_val = value * 3

    # Ensure min < max
    if min_val > max_val:
        min_val, max_val = max_val, min_val

    return (min_val, max_val, step)


def render_all_sections() -> Dict[str, float]:
    """
    Render parameter sliders for all tunable parameters.

    Returns:
        Dict mapping parameter name to slider value
    """
    slider_values = {}

    st.sidebar.subheader("Device Parameters")

    # Build a lookup dict for parameters from slot definitions
    param_info = {}
    for slot_id, slot_def in DEVICE_SLOTS.items():
        for param in slot_def.get("parameters", []):
            name = param.get("name")
            if name:
                param_info[name] = {
                    "default": param.get("default_value", 1.0),
                    "min": param.get("min_value", 0.01),
                    "max": param.get("max_value", 10.0),
                    "step": param.get("step", 0.1),
                    "label": param.get("label", name.replace("_", " ").title())
                }

    # Top-level tunables (the parametric contract's knobs) arrive via
    # GLOBAL_PARAMS as a list of dicts carrying the script's REAL defaults
    # and analysis-derived ranges — without this, sliders would initialize
    # to a fabricated 1.0 and silently rebuild a wrong device.
    for gp in (GLOBAL_PARAMS or []):
        if isinstance(gp, dict) and gp.get("name"):
            param_info[gp["name"]] = {
                "default": gp.get("default_value", 1.0),
                "min": gp.get("min_value", 0.01),
                "max": gp.get("max_value", 10.0),
                "step": gp.get("step", 0.1),
                "label": gp.get("label", gp["name"].replace("_", " ").title()),
            }

    # Render slider for each tunable parameter
    for param_name in TUNABLE_PARAMS:
        # Get parameter info from slot definitions if available
        info = param_info.get(param_name)

        if info:
            default_value = info["default"]
            min_val = info["min"]
            max_val = info["max"]
            step = info["step"]
            label = info["label"]
        else:
            # Fall back to session state or default
            default_value = st.session_state.get(f"param_{param_name}", 1.0)
            min_val, max_val, step = _suggest_slider_range(default_value, param_name)
            label = param_name.replace("_", " ").title()

        # Create session state key
        state_key = f"param_{param_name}"
        if state_key not in st.session_state:
            st.session_state[state_key] = default_value

        # Ensure value is within range
        current_val = st.session_state[state_key]
        current_val = max(min_val, min(max_val, current_val))

        # Create slider
        value = st.sidebar.slider(
            label,
            min_value=float(min_val),
            max_value=float(max_val),
            value=float(current_val),
            step=float(step),
            key=f"{param_name}_slider",
            help=f"Adjust {param_name}"
        )

        st.session_state[state_key] = value
        slider_values[param_name] = value

    return slider_values


def render_quick_presets() -> None:
    """Render preset buttons for quick configuration."""
    st.sidebar.subheader("Quick Presets")

    col1, col2 = st.sidebar.columns(2)

    with col1:
        if st.button("Default", key="preset_default", use_container_width=True):
            _apply_preset("default")

    with col2:
        if st.button("Minimum", key="preset_minimum", use_container_width=True):
            _apply_preset("minimum")

    col3, col4 = st.sidebar.columns(2)

    with col3:
        if st.button("Maximum", key="preset_maximum", use_container_width=True):
            _apply_preset("maximum")

    with col4:
        if st.button("Random", key="preset_random", use_container_width=True):
            _apply_preset("random")


def _apply_preset(preset_name: str) -> None:
    """Apply a preset configuration."""
    import random

    # Build param info lookup
    param_info = {}
    for slot_id, slot_def in DEVICE_SLOTS.items():
        for param in slot_def.get("parameters", []):
            name = param.get("name")
            if name:
                param_info[name] = {
                    "default": param.get("default_value", 1.0),
                    "min": param.get("min_value", 0.01),
                    "max": param.get("max_value", 10.0),
                    "step": param.get("step", 0.1),
                }
    for gp in (GLOBAL_PARAMS or []):
        if isinstance(gp, dict) and gp.get("name"):
            param_info[gp["name"]] = {
                "default": gp.get("default_value", 1.0),
                "min": gp.get("min_value", 0.01),
                "max": gp.get("max_value", 10.0),
                "step": gp.get("step", 0.1),
            }

    for param_name in TUNABLE_PARAMS:
        info = param_info.get(param_name)
        if info:
            default_value = info["default"]
            min_val = info["min"]
            max_val = info["max"]
            step = info["step"]
        else:
            default_value = 1.0
            min_val, max_val, step = _suggest_slider_range(default_value, param_name)

        state_key = f"param_{param_name}"

        if preset_name == "default":
            st.session_state[state_key] = default_value
        elif preset_name == "minimum":
            st.session_state[state_key] = min_val
        elif preset_name == "maximum":
            st.session_state[state_key] = max_val
        elif preset_name == "random":
            # Random value within range
            range_size = max_val - min_val
            random_val = min_val + random.random() * range_size
            # Round to step
            random_val = round(random_val / step) * step
            st.session_state[state_key] = random_val


def render_custom_primitives_sidebar() -> None:
    """Render the custom primitives section in the sidebar."""
    st.sidebar.header("Custom Primitives")

    # Add new primitive button
    with st.sidebar.expander("➕ Add New Primitive", expanded=False):
        new_type = st.selectbox(
            "Primitive Type",
            options=list(PRIMITIVE_TYPES.keys()),
            key="new_primitive_type"
        )

        new_x = st.slider("X Position", -4.0, 4.0, 0.0, 0.05, key="new_prim_x")
        new_y = st.slider("Y Position", -3.0, 3.0, 0.0, 0.05, key="new_prim_y")

        new_layer = st.selectbox(
            "Layer",
            options=["Layer 1 (blue)", "Layer 2 (orange)", "Custom (green)"],
            key="new_prim_layer"
        )

        # Show type-specific parameters
        new_params = {}
        prim_info = PRIMITIVE_TYPES[new_type]
        for param in prim_info["params"]:
            default = prim_info["defaults"][param]
            new_params[param] = st.slider(
                param.capitalize(),
                0.05, 2.0, default, 0.05,
                key=f"new_prim_{param}"
            )

        if st.button("Add Primitive", use_container_width=True, type="primary"):
            # Map layer selection to actual layer
            layer_map = {
                "Layer 1 (blue)": (1, 0),
                "Layer 2 (orange)": (2, 0),
                "Custom (green)": (3, 0),
            }

            new_primitive = {
                "id": len(st.session_state.custom_primitives),
                "type": new_type,
                "x": new_x,
                "y": new_y,
                "layer": layer_map[new_layer],
                "layer_name": new_layer,
                "params": new_params.copy()
            }
            st.session_state.custom_primitives.append(new_primitive)
            st.rerun()

    # Show existing custom primitives
    if st.session_state.custom_primitives:
        st.sidebar.markdown(f"**Added Primitives ({len(st.session_state.custom_primitives)})**")

        primitives_to_delete = []

        for i, prim in enumerate(st.session_state.custom_primitives):
            with st.sidebar.expander(f"#{i+1}: {prim['type'].capitalize()} @ ({prim['x']:.2f}, {prim['y']:.2f})"):
                # Edit position
                new_x = st.slider(
                    "X", -4.0, 4.0, prim['x'], 0.05,
                    key=f"edit_prim_{i}_x"
                )
                new_y = st.slider(
                    "Y", -3.0, 3.0, prim['y'], 0.05,
                    key=f"edit_prim_{i}_y"
                )

                # Edit size params
                for param in PRIMITIVE_TYPES[prim['type']]["params"]:
                    prim['params'][param] = st.slider(
                        param.capitalize(),
                        0.05, 2.0, prim['params'].get(param, 0.3), 0.05,
                        key=f"edit_prim_{i}_{param}"
                    )

                # Update position
                prim['x'] = new_x
                prim['y'] = new_y

                # Delete button
                if st.button(f"🗑️ Delete", key=f"del_prim_{i}", use_container_width=True):
                    primitives_to_delete.append(i)

        # Delete marked primitives
        for idx in reversed(primitives_to_delete):
            st.session_state.custom_primitives.pop(idx)
            st.rerun()

        # Clear all button
        if st.sidebar.button("Clear All Primitives", use_container_width=True):
            st.session_state.custom_primitives = []
            st.rerun()
    else:
        st.sidebar.caption("No custom primitives added yet.")


def get_config_summary(config: Dict[str, Dict[str, Any]]) -> Dict[str, str]:
    """
    Get a summary of current configuration (type for each slot).
    """
    return {
        slot_id: cfg["type"]
        for slot_id, cfg in config.items()
    }
