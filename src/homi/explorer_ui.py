"""
Explorer UI Generators for HOMI

Provides Streamlit UI components for the interactive explorer.
Adapted from Weber for embedded use in the main HOMI app.
"""

import streamlit as st
import random
from typing import Dict, Any, List, Tuple, Optional

# Primitive types for custom primitives
PRIMITIVE_TYPES = {
    "rectangle": {"params": ["width", "height"], "defaults": {"width": 0.5, "height": 0.3}},
    "circle": {"params": ["radius"], "defaults": {"radius": 0.2}},
    "ellipse": {"params": ["rx", "ry"], "defaults": {"rx": 0.3, "ry": 0.2}},
    "triangle": {"params": ["x", "y"], "defaults": {"x": 0.3, "y": 0.3}},
    "straight": {"params": ["length", "width"], "defaults": {"length": 1.0, "width": 0.3}},
}


def init_explorer_state():
    """Initialize session state for the explorer."""
    if "explorer_slider_values" not in st.session_state:
        st.session_state.explorer_slider_values = {}
    if "explorer_custom_primitives" not in st.session_state:
        st.session_state.explorer_custom_primitives = []


def render_parameter_sliders(
    parameters: List[Dict[str, Any]],
    prefix: str = "explorer"
) -> Dict[str, float]:
    """
    Render parameter sliders in the sidebar.

    Args:
        parameters: List of parameter dicts with name, label, min_value, max_value, default_value, step
        prefix: Prefix for session state keys

    Returns:
        Dict mapping parameter name to current slider value
    """
    slider_values = {}

    for param in parameters:
        name = param["name"]
        label = param.get("label", name.replace("_", " ").title())
        min_val = float(param.get("min_value", 0.01))
        max_val = float(param.get("max_value", 10.0))
        default_val = float(param.get("default_value", 1.0))
        step = float(param.get("step", 0.1))

        # Session state key
        state_key = f"{prefix}_{name}"

        # Initialize if needed
        if state_key not in st.session_state:
            st.session_state[state_key] = default_val

        # Ensure value is within range
        current_val = st.session_state[state_key]
        current_val = max(min_val, min(max_val, current_val))

        # Create slider
        value = st.sidebar.slider(
            label,
            min_value=min_val,
            max_value=max_val,
            value=current_val,
            step=step,
            key=f"{state_key}_slider",
            help=f"Adjust {name}"
        )

        st.session_state[state_key] = value
        slider_values[name] = value

    return slider_values


def render_quick_presets(
    parameters: List[Dict[str, Any]],
    prefix: str = "explorer"
) -> None:
    """
    Render preset buttons for quick configuration.

    Args:
        parameters: List of parameter dicts
        prefix: Prefix for session state keys
    """
    st.sidebar.subheader("Quick Presets")

    col1, col2 = st.sidebar.columns(2)

    with col1:
        if st.button("Default", key=f"{prefix}_preset_default", use_container_width=True):
            _apply_preset(parameters, "default", prefix)

    with col2:
        if st.button("Minimum", key=f"{prefix}_preset_minimum", use_container_width=True):
            _apply_preset(parameters, "minimum", prefix)

    col3, col4 = st.sidebar.columns(2)

    with col3:
        if st.button("Maximum", key=f"{prefix}_preset_maximum", use_container_width=True):
            _apply_preset(parameters, "maximum", prefix)

    with col4:
        if st.button("Random", key=f"{prefix}_preset_random", use_container_width=True):
            _apply_preset(parameters, "random", prefix)


def _apply_preset(
    parameters: List[Dict[str, Any]],
    preset_name: str,
    prefix: str
) -> None:
    """Apply a preset configuration."""
    for param in parameters:
        name = param["name"]
        min_val = float(param.get("min_value", 0.01))
        max_val = float(param.get("max_value", 10.0))
        default_val = float(param.get("default_value", 1.0))
        step = float(param.get("step", 0.1))

        state_key = f"{prefix}_{name}"

        if preset_name == "default":
            st.session_state[state_key] = default_val
        elif preset_name == "minimum":
            st.session_state[state_key] = min_val
        elif preset_name == "maximum":
            st.session_state[state_key] = max_val
        elif preset_name == "random":
            range_size = max_val - min_val
            random_val = min_val + random.random() * range_size
            random_val = round(random_val / step) * step
            st.session_state[state_key] = random_val


def render_custom_primitives_sidebar() -> None:
    """Render the custom primitives section in the sidebar."""
    st.sidebar.subheader("Custom Primitives")

    # Add new primitive button
    with st.sidebar.expander("Add New Primitive", expanded=False):
        new_type = st.selectbox(
            "Primitive Type",
            options=list(PRIMITIVE_TYPES.keys()),
            key="explorer_new_primitive_type"
        )

        new_x = st.slider("X Position", -4.0, 4.0, 0.0, 0.05, key="explorer_new_prim_x")
        new_y = st.slider("Y Position", -3.0, 3.0, 0.0, 0.05, key="explorer_new_prim_y")

        new_layer = st.selectbox(
            "Layer",
            options=["Layer 1 (blue)", "Layer 2 (orange)", "Custom (green)"],
            key="explorer_new_prim_layer"
        )

        # Show type-specific parameters
        new_params = {}
        prim_info = PRIMITIVE_TYPES[new_type]
        for param in prim_info["params"]:
            default = prim_info["defaults"][param]
            new_params[param] = st.slider(
                param.capitalize(),
                0.05, 2.0, default, 0.05,
                key=f"explorer_new_prim_{param}"
            )

        if st.button("Add Primitive", use_container_width=True, type="primary"):
            layer_map = {
                "Layer 1 (blue)": (1, 0),
                "Layer 2 (orange)": (2, 0),
                "Custom (green)": (3, 0),
            }

            new_primitive = {
                "id": len(st.session_state.explorer_custom_primitives),
                "type": new_type,
                "x": new_x,
                "y": new_y,
                "layer": layer_map[new_layer],
                "layer_name": new_layer,
                "params": new_params.copy()
            }
            st.session_state.explorer_custom_primitives.append(new_primitive)
            st.rerun()

    # Show existing custom primitives
    if st.session_state.explorer_custom_primitives:
        st.sidebar.markdown(f"**Added ({len(st.session_state.explorer_custom_primitives)})**")

        primitives_to_delete = []

        for i, prim in enumerate(st.session_state.explorer_custom_primitives):
            with st.sidebar.expander(f"#{i+1}: {prim['type'].capitalize()} @ ({prim['x']:.2f}, {prim['y']:.2f})"):
                # Edit position
                new_x = st.slider("X", -4.0, 4.0, prim['x'], 0.05, key=f"explorer_edit_prim_{i}_x")
                new_y = st.slider("Y", -3.0, 3.0, prim['y'], 0.05, key=f"explorer_edit_prim_{i}_y")

                # Edit size params
                for param in PRIMITIVE_TYPES[prim['type']]["params"]:
                    prim['params'][param] = st.slider(
                        param.capitalize(),
                        0.05, 2.0, prim['params'].get(param, 0.3), 0.05,
                        key=f"explorer_edit_prim_{i}_{param}"
                    )

                # Update position
                prim['x'] = new_x
                prim['y'] = new_y

                if st.button(f"Delete", key=f"explorer_del_prim_{i}", use_container_width=True):
                    primitives_to_delete.append(i)

        for idx in reversed(primitives_to_delete):
            st.session_state.explorer_custom_primitives.pop(idx)
            st.rerun()

        if st.sidebar.button("Clear All", use_container_width=True):
            st.session_state.explorer_custom_primitives = []
            st.rerun()
    else:
        st.sidebar.caption("No custom primitives added yet.")


def add_custom_primitives_to_component(component, primitives: List[Dict]) -> None:
    """
    Add custom primitives to a GDSFactory component.

    Args:
        component: GDSFactory Component to modify (in place)
        primitives: List of primitive dicts
    """
    import gdsfactory as gf

    for prim in primitives:
        prim_type = prim["type"]
        layer = prim["layer"]
        params = prim["params"]
        x, y = prim["x"], prim["y"]

        try:
            if prim_type == "rectangle":
                prim_comp = gf.components.rectangle(
                    size=(params.get("width", 0.5), params.get("height", 0.3)),
                    layer=layer,
                    centered=True
                )
            elif prim_type == "circle":
                prim_comp = gf.components.circle(
                    radius=params.get("radius", 0.2),
                    layer=layer
                )
            elif prim_type == "ellipse":
                prim_comp = gf.components.ellipse(
                    radii=(params.get("rx", 0.3), params.get("ry", 0.2)),
                    layer=layer
                )
            elif prim_type == "triangle":
                prim_comp = gf.components.triangle(
                    x=params.get("x", 0.3),
                    y=params.get("y", 0.3),
                    layer=layer
                )
            elif prim_type == "straight":
                # Create cross-section for straight waveguide
                xs = gf.cross_section.cross_section(
                    width=params.get("width", 0.3),
                    layer=layer
                )
                prim_comp = gf.components.straight(
                    length=params.get("length", 1.0),
                    cross_section=xs
                )
            else:
                continue

            ref = component.add_ref(prim_comp)
            ref.move((x, y))
        except Exception:
            pass  # Skip failed primitives
