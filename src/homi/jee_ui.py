"""
JEE UI Module for HOMI

Streamlit UI components for the JEE optimization step (Step 5.5).
Includes presets for quick selection and advanced controls for full GDSExplorer access.
"""

from typing import Any, Dict, List, Optional
import streamlit as st


# =============================================================================
# OPTIMIZATION PRESETS
# =============================================================================

OPTIMIZATION_PRESETS = {
    "quick": {
        "name": "Quick",
        "description": "Fast single-method (~30s)",
        "mode": "single",
        "method": "Powell",
        "max_iterations": 50,
        "footprint_penalty_enabled": True,
        "footprint_penalty_weight": 1.0,
        "footprint_penalty_mode": "match",
    },
    "balanced": {
        "name": "Balanced",
        "description": "Reliable optimization (~1-2 min)",
        "mode": "single",
        "method": "Nelder-Mead",
        "max_iterations": 100,
        "footprint_penalty_enabled": True,
        "footprint_penalty_weight": 1.0,
        "footprint_penalty_mode": "match",
    },
    "thorough": {
        "name": "Thorough",
        "description": "Grid + local opt (~3-5 min)",
        "mode": "explorer",
        "grid_points_per_param": 3,
        "top_n_for_optimization": 3,
        "methods": ["Nelder-Mead"],
        "max_iterations_per_method": 100,
        "parallel_workers": 2,
        "footprint_penalty_enabled": True,
        "footprint_penalty_weight": 1.0,
        "footprint_penalty_mode": "match",
    },
    "maximum": {
        "name": "Maximum",
        "description": "Grid + parallel methods (~5-10 min)",
        "mode": "explorer",
        "grid_points_per_param": 5,
        "top_n_for_optimization": 3,
        "methods": ["Powell", "Nelder-Mead"],
        "max_iterations_per_method": 150,
        "parallel_workers": 4,
        "footprint_penalty_enabled": True,
        "footprint_penalty_weight": 1.0,
        "footprint_penalty_mode": "match",
    },
}


def render_preset_selection() -> Optional[str]:
    """
    Render preset selection buttons.

    Returns:
        Selected preset key or None if no selection
    """
    st.markdown("**Optimization Strength**")

    cols = st.columns(4)
    selected = st.session_state.get("jee_preset", "balanced")

    for i, (key, preset) in enumerate(OPTIMIZATION_PRESETS.items()):
        with cols[i]:
            is_selected = selected == key
            button_type = "primary" if is_selected else "secondary"

            if st.button(
                f"**{preset['name']}**",
                key=f"preset_{key}",
                type=button_type,
                use_container_width=True,
                help=preset["description"],
            ):
                st.session_state.jee_preset = key
                _apply_preset_to_session(key)
                st.rerun()

    # Show description of selected preset
    if selected in OPTIMIZATION_PRESETS:
        preset = OPTIMIZATION_PRESETS[selected]
        mode_desc = "Single method" if preset["mode"] == "single" else "Grid search + parallel methods"
        st.caption(f"_{preset['description']}_ — {mode_desc}")

    return selected


def _apply_preset_to_session(preset_key: str) -> None:
    """Apply preset settings to session state."""
    if preset_key not in OPTIMIZATION_PRESETS:
        return

    preset = OPTIMIZATION_PRESETS[preset_key]
    st.session_state.jee_config = {
        "mode": preset.get("mode", "single"),
        "method": preset.get("method", "Nelder-Mead"),
        "max_iterations": preset.get("max_iterations", 100),
        "max_function_evals": preset.get("max_iterations", 100) * 2,
        "grid_points_per_param": preset.get("grid_points_per_param", 5),
        "top_n_for_optimization": preset.get("top_n_for_optimization", 3),
        "methods": preset.get("methods", ["Nelder-Mead"]),
        "max_iterations_per_method": preset.get("max_iterations_per_method", 100),
        "parallel_workers": preset.get("parallel_workers", 4),
        "footprint_penalty_enabled": preset.get("footprint_penalty_enabled", True),
        "footprint_penalty_weight": preset.get("footprint_penalty_weight", 1.0),
        "footprint_penalty_mode": preset.get("footprint_penalty_mode", "match"),
    }


def render_advanced_optimization_config() -> Dict[str, Any]:
    """
    Render full advanced optimization controls in an expander.

    Returns:
        Dict with all configuration settings including explorer mode options
    """
    with st.expander("Advanced Optimization Settings", expanded=False):
        # Get current config from session or defaults
        current = st.session_state.get("jee_config", {})

        # Mode selection
        mode_options = ["Single Method", "Grid + Parallel (Explorer)"]
        current_mode = current.get("mode", "single")
        mode_index = 0 if current_mode == "single" else 1

        mode = st.radio(
            "Optimization Mode",
            mode_options,
            index=mode_index,
            horizontal=True,
            help="Single method is faster; Explorer mode tries multiple methods in parallel."
        )

        is_explorer = mode == "Grid + Parallel (Explorer)"

        st.divider()

        if not is_explorer:
            # Single method settings
            col1, col2 = st.columns(2)

            with col1:
                method = st.selectbox(
                    "Method",
                    options=["Nelder-Mead", "Powell", "COBYLA"],
                    index=["Nelder-Mead", "Powell", "COBYLA"].index(current.get("method", "Nelder-Mead")),
                    help="Nelder-Mead is typically most reliable."
                )

            with col2:
                max_iterations = st.slider(
                    "Max Iterations",
                    min_value=50,
                    max_value=500,
                    value=current.get("max_iterations", 100),
                    step=10,
                )

            config = {
                "mode": "single",
                "method": method,
                "max_iterations": max_iterations,
                "max_function_evals": max_iterations * 2,
            }

        else:
            # Explorer mode settings
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**Grid Search**")
                grid_points = st.slider(
                    "Grid Points per Parameter",
                    min_value=2,
                    max_value=10,
                    value=current.get("grid_points_per_param", 5),
                    help="More points = better coverage but slower"
                )

                top_n = st.slider(
                    "Top N for Local Optimization",
                    min_value=1,
                    max_value=10,
                    value=current.get("top_n_for_optimization", 3),
                    help="Number of best grid points to optimize from"
                )

            with col2:
                st.markdown("**Local Optimization**")

                # Check if CMA-ES is available
                try:
                    import cma
                    available_methods = ["Powell", "Nelder-Mead", "CMA-ES"]
                except ImportError:
                    available_methods = ["Powell", "Nelder-Mead"]

                methods = st.multiselect(
                    "Methods to Run",
                    options=available_methods,
                    default=current.get("methods", ["Powell", "Nelder-Mead"]),
                    help="Select which optimization methods to run in parallel"
                )

                if not methods:
                    methods = ["Nelder-Mead"]
                    st.warning("At least one method required")

                max_iter_per = st.slider(
                    "Max Iterations per Method",
                    min_value=50,
                    max_value=300,
                    value=current.get("max_iterations_per_method", 100),
                    step=10,
                )

                parallel_workers = st.slider(
                    "Parallel Workers",
                    min_value=1,
                    max_value=8,
                    value=current.get("parallel_workers", 4),
                    help="Number of parallel optimization threads"
                )

            config = {
                "mode": "explorer",
                "grid_points_per_param": grid_points,
                "top_n_for_optimization": top_n,
                "methods": methods,
                "max_iterations_per_method": max_iter_per,
                "parallel_workers": parallel_workers,
            }

        # Footprint settings (both modes)
        st.divider()
        st.markdown("**Footprint Constraint**")

        fp_col1, fp_col2, fp_col3 = st.columns(3)

        with fp_col1:
            fp_enabled = st.checkbox(
                "Enable Penalty",
                value=current.get("footprint_penalty_enabled", True),
            )

        with fp_col2:
            fp_weight = st.slider(
                "Penalty Weight",
                min_value=0.1,
                max_value=10.0,
                value=current.get("footprint_penalty_weight", 1.0),
                step=0.1,
                disabled=not fp_enabled,
            )

        with fp_col3:
            fp_mode = st.selectbox(
                "Mode",
                options=["match", "exceed"],
                index=0 if current.get("footprint_penalty_mode", "match") == "match" else 1,
                disabled=not fp_enabled,
                help="'match' penalizes any size difference; 'exceed' only penalizes exceeding bounds."
            )

        config.update({
            "footprint_penalty_enabled": fp_enabled,
            "footprint_penalty_weight": fp_weight if fp_enabled else 1.0,
            "footprint_penalty_mode": fp_mode if fp_enabled else "match",
        })

    # Update session state
    st.session_state.jee_config = config

    return config


def render_optimization_config() -> Dict[str, Any]:
    """
    Render optimization configuration UI.

    Returns:
        Dict with configuration settings:
            - max_iterations: int (50-300)
            - max_function_evals: int (100-500)
            - method: str ("Nelder-Mead", "Powell", "COBYLA")
            - footprint_penalty_enabled: bool
            - footprint_penalty_weight: float (0.1-10.0)
            - footprint_penalty_mode: str ("exceed" or "match")
    """
    col1, col2 = st.columns(2)

    with col1:
        max_iterations = st.slider(
            "Max Iterations",
            min_value=50,
            max_value=300,
            value=100,
            step=10,
            help="Maximum optimization iterations. More iterations may improve results but take longer."
        )

        method = st.selectbox(
            "Optimization Method",
            options=["Nelder-Mead", "Powell", "COBYLA"],
            index=0,
            help="Nelder-Mead is typically most reliable for this type of optimization."
        )

    with col2:
        footprint_penalty_enabled = st.checkbox(
            "Enable Footprint Constraint",
            value=True,
            help="Penalize designs that exceed the target footprint."
        )

        if footprint_penalty_enabled:
            footprint_penalty_weight = st.slider(
                "Footprint Penalty Weight",
                min_value=0.1,
                max_value=10.0,
                value=1.0,
                step=0.1,
                help="Higher values more strongly penalize footprint violations."
            )

            footprint_penalty_mode = st.selectbox(
                "Footprint Mode",
                options=["match", "exceed"],
                index=0,
                help="'match' penalizes any size difference; 'exceed' only penalizes exceeding bounds."
            )
        else:
            footprint_penalty_weight = 1.0
            footprint_penalty_mode = "match"

    # Max function evals is derived from iterations
    max_function_evals = max_iterations * 2

    return {
        "max_iterations": max_iterations,
        "max_function_evals": max_function_evals,
        "method": method,
        "footprint_penalty_enabled": footprint_penalty_enabled,
        "footprint_penalty_weight": footprint_penalty_weight,
        "footprint_penalty_mode": footprint_penalty_mode,
    }


def render_optimization_progress(
    iteration: int,
    best_sse: float,
    best_total_cost: float,
    history: List[Dict],
    max_iterations: int = 100,
) -> None:
    """
    Render live optimization progress.

    Args:
        iteration: Current iteration number
        best_sse: Current best SSE value
        best_total_cost: Current best total cost
        history: List of history dicts with sse values
        max_iterations: Maximum iterations for progress bar
    """
    # Progress bar
    progress = min(iteration / max_iterations, 1.0)
    st.progress(progress, text=f"Iteration {iteration} / {max_iterations}")

    # Metrics row
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Best SSE",
            f"{best_sse:,.0f}" if best_sse < float('inf') else "N/A"
        )

    with col2:
        st.metric(
            "Best Total Cost",
            f"{best_total_cost:,.0f}" if best_total_cost < float('inf') else "N/A"
        )

    with col3:
        # Calculate improvement from first to current best
        if history and len(history) > 1:
            initial_sse = history[0].get("sse", float('inf'))
            if initial_sse > 0 and initial_sse < float('inf') and best_sse < float('inf'):
                improvement = ((initial_sse - best_sse) / initial_sse) * 100
                st.metric("Improvement", f"{improvement:.1f}%")
            else:
                st.metric("Improvement", "0%")
        else:
            st.metric("Improvement", "0%")

    # SSE history chart
    if history and len(history) > 1:
        import pandas as pd

        # Extract SSE values over iterations
        sse_data = [
            {"iteration": h["iteration"], "SSE": h["sse"]}
            for h in history
            if h.get("sse", float('inf')) < float('inf')
        ]

        if sse_data:
            df = pd.DataFrame(sse_data)
            st.line_chart(df.set_index("iteration")["SSE"], use_container_width=True)


def render_optimization_results(result: Dict[str, Any]) -> None:
    """
    Render optimization results comparison.

    Args:
        result: Dict with optimization results:
            - baseline_sse: float
            - best_sse: float
            - improvement_pct: float
            - best_params: dict
            - iterations: int
            - within_footprint: bool
    """
    # Success/status message
    improvement_pct = result.get("improvement_pct", 0)
    if improvement_pct > 0:
        st.success(f"Optimization improved SSE by {improvement_pct:.1f}%")
    elif improvement_pct == 0:
        st.info("No improvement found - baseline was already optimal for this parameter space.")
    else:
        st.warning("Optimization did not improve results.")

    # Metrics comparison
    st.subheader("Results Comparison")

    col1, col2, col3 = st.columns(3)

    with col1:
        baseline_sse = result.get("baseline_sse", 0)
        st.metric(
            "Baseline SSE",
            f"{baseline_sse:,.0f}" if baseline_sse > 0 else "N/A"
        )

    with col2:
        best_sse = result.get("best_sse", 0)
        delta = None
        if baseline_sse > 0 and best_sse > 0:
            delta = f"-{baseline_sse - best_sse:,.0f}"
        st.metric(
            "Optimized SSE",
            f"{best_sse:,.0f}" if best_sse > 0 else "N/A",
            delta=delta,
            delta_color="normal"
        )

    with col3:
        st.metric(
            "Iterations",
            result.get("iterations", 0)
        )

    # Footprint status
    if result.get("within_footprint") is not None:
        if result["within_footprint"]:
            st.info("Device is within footprint constraints.")
        else:
            st.warning("Device exceeds footprint constraints.")

    # Best parameters (collapsible)
    best_params = result.get("best_params", {})
    if best_params:
        with st.expander("Optimized Parameters", expanded=False):
            import pandas as pd
            params_df = pd.DataFrame([
                {"Parameter": k, "Value": f"{v:.4f}"}
                for k, v in best_params.items()
            ])
            st.dataframe(params_df, hide_index=True, use_container_width=True)


def render_parameter_preview(params: List[Dict[str, Any]], max_display: int = 10) -> None:
    """
    Render a preview table of parameters that will be optimized.

    Args:
        params: List of parameter dicts with name, default_value, min_value, max_value
        max_display: Maximum number of parameters to display
    """
    import pandas as pd

    # Filter to numeric, non-layer parameters
    filtered = [
        p for p in params
        if isinstance(p.get("default_value"), (int, float))
        and "layer" not in p.get("name", "").lower()
    ]

    if not filtered:
        st.warning("No tunable parameters detected in the generated script.")
        return

    # Create dataframe for display
    display_params = filtered[:max_display]
    param_df = pd.DataFrame([
        {
            "Parameter": p["name"],
            "Current": f"{p['default_value']:.4f}",
            "Min": f"{p['min_value']:.4f}",
            "Max": f"{p['max_value']:.4f}",
        }
        for p in display_params
    ])

    st.dataframe(param_df, hide_index=True, use_container_width=True)

    if len(filtered) > max_display:
        st.caption(f"... and {len(filtered) - max_display} more parameters")


def init_jee_session_state() -> None:
    """Initialize JEE-related session state variables."""
    if "jee_enabled" not in st.session_state:
        st.session_state.jee_enabled = True
    if "jee_running" not in st.session_state:
        st.session_state.jee_running = False
    if "jee_complete" not in st.session_state:
        st.session_state.jee_complete = False
    if "jee_result" not in st.session_state:
        st.session_state.jee_result = None
    if "jee_preset" not in st.session_state:
        st.session_state.jee_preset = "balanced"
    if "jee_config" not in st.session_state:
        # Default to balanced preset settings
        st.session_state.jee_config = {
            "mode": "single",
            "method": "Nelder-Mead",
            "max_iterations": 100,
            "max_function_evals": 200,
            # Explorer mode settings
            "grid_points_per_param": 5,
            "top_n_for_optimization": 3,
            "methods": ["Powell", "Nelder-Mead"],
            "max_iterations_per_method": 100,
            "parallel_workers": 4,
            # Footprint settings
            "footprint_penalty_enabled": True,
            "footprint_penalty_weight": 1.0,
            "footprint_penalty_mode": "match",
        }
