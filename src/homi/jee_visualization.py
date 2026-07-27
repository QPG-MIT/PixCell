"""
JEE Optimization Visualization Module

Provides real-time convergence visualization for JEE optimization.
Displays SSE progress, stats grid, and method comparison for explorer mode.
"""

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import plotly.graph_objects as go


# Color scheme (dark theme matching exploration_tree.py)
COLORS = {
    "background": "#1e293b",
    "paper": "#0f172a",
    "text": "#f1f5f9",
    "text_dim": "#94a3b8",
    "grid": "#334155",
    "sse_line": "#f59e0b",       # Amber - main SSE line
    "best_point": "#22c55e",     # Green - best point marker
    "baseline": "#ef4444",        # Red - baseline reference
    "current": "#3b82f6",         # Blue - current iteration
    "improvement": "#22c55e",     # Green - improvement indicator
    "footprint_ok": "#22c55e",    # Green
    "footprint_bad": "#ef4444",   # Red
}

# Method colors for explorer mode
METHOD_COLORS = {
    "Powell": "#3b82f6",          # Blue
    "Nelder-Mead": "#f59e0b",     # Amber
    "CMA-ES": "#8b5cf6",          # Purple
    "COBYLA": "#22c55e",          # Green
}


@dataclass
class OptimizationState:
    """State for tracking optimization progress."""
    # Configuration
    mode: str = "single"                  # "single" or "explorer"
    method: str = "Nelder-Mead"           # Current/primary method
    max_iterations: int = 100

    # Progress tracking
    current_iteration: int = 0
    phase: str = "optimizing"             # "grid_search", "optimizing", "complete"

    # Metrics
    baseline_sse: float = 0.0
    best_sse: float = float('inf')
    current_sse: float = 0.0
    best_total_cost: float = float('inf')
    best_footprint_penalty: float = 0.0
    within_footprint: bool = True

    # Parameters
    baseline_params: Dict[str, float] = field(default_factory=dict)
    best_params: Dict[str, float] = field(default_factory=dict)
    current_params: Dict[str, float] = field(default_factory=dict)

    # History
    history: List[Dict] = field(default_factory=list)
    start_time: float = field(default_factory=time.time)

    # Explorer mode: multiple methods
    methods_running: List[str] = field(default_factory=list)
    method_results: Dict[str, Dict] = field(default_factory=dict)
    grid_points_evaluated: int = 0
    grid_best_sse: float = float('inf')

    # For debouncing
    last_render_time: float = 0.0
    update_counter: int = 0


def initialize_optimization_state(
    mode: str = "single",
    method: str = "Nelder-Mead",
    max_iterations: int = 100,
    baseline_sse: float = 0.0,
    baseline_params: Optional[Dict[str, float]] = None,
    methods: Optional[List[str]] = None,
) -> OptimizationState:
    """Initialize a new optimization state.

    Args:
        mode: "single" for single method, "explorer" for grid + parallel
        method: Primary optimization method
        max_iterations: Maximum iterations for single mode
        baseline_sse: Initial SSE before optimization
        baseline_params: Initial parameter values
        methods: List of methods for explorer mode

    Returns:
        Initialized OptimizationState
    """
    state = OptimizationState(
        mode=mode,
        method=method,
        max_iterations=max_iterations,
        baseline_sse=baseline_sse,
        best_sse=baseline_sse,
        current_sse=baseline_sse,
        baseline_params=baseline_params or {},
        best_params=baseline_params.copy() if baseline_params else {},
        current_params=baseline_params.copy() if baseline_params else {},
        start_time=time.time(),
    )

    if mode == "explorer" and methods:
        state.methods_running = methods
        state.method_results = {m: {} for m in methods}

    return state


def update_state_from_callback(state: OptimizationState, event: Dict) -> None:
    """Update state from optimization callback event.

    Args:
        state: Current optimization state to update
        event: Callback event dict with iteration data
    """
    event_type = event.get("type", "iteration")

    if event_type == "iteration_update" or event_type == "iteration":
        state.current_iteration = event.get("iteration", state.current_iteration)
        state.current_sse = event.get("sse", state.current_sse)

        # Update best if improved
        if state.current_sse < state.best_sse:
            state.best_sse = state.current_sse
            if "params" in event:
                state.best_params = event["params"].copy()

        state.best_total_cost = event.get("best_total_cost", state.best_total_cost)
        state.best_footprint_penalty = event.get("footprint_penalty", state.best_footprint_penalty)
        state.within_footprint = event.get("within_footprint", state.within_footprint)

        if "params" in event:
            state.current_params = event["params"]

        # Add to history
        state.history.append({
            "iteration": state.current_iteration,
            "sse": state.current_sse,
            "best_sse": state.best_sse,
        })

    elif event_type == "grid_progress":
        state.phase = "grid_search"
        state.grid_points_evaluated = event.get("points_evaluated", 0)
        state.grid_best_sse = event.get("best_sse", state.grid_best_sse)

    elif event_type == "method_start":
        method = event.get("method", "")
        if method and method not in state.method_results:
            state.method_results[method] = {"status": "running", "history": []}

    elif event_type == "method_update":
        method = event.get("method", "")
        if method in state.method_results:
            state.method_results[method].update({
                "iteration": event.get("iteration", 0),
                "sse": event.get("sse", 0),
                "best_sse": event.get("best_sse", 0),
            })
            if "history" not in state.method_results[method]:
                state.method_results[method]["history"] = []
            state.method_results[method]["history"].append({
                "iteration": event.get("iteration", 0),
                "sse": event.get("sse", 0),
            })

    elif event_type == "method_complete":
        method = event.get("method", "")
        if method in state.method_results:
            state.method_results[method].update({
                "status": "complete",
                "best_sse": event.get("best_sse", 0),
                "best_params": event.get("best_params", {}),
                "improvement_pct": event.get("improvement_pct", 0),
            })

    elif event_type == "complete":
        state.phase = "complete"
        state.best_sse = event.get("best_sse", state.best_sse)
        if "best_params" in event:
            state.best_params = event["best_params"]

    state.update_counter += 1


def create_convergence_figure(
    state: OptimizationState,
    height: int = 300,
    show_baseline: bool = True,
) -> go.Figure:
    """Create Plotly figure showing SSE convergence over iterations.

    Args:
        state: Current optimization state
        height: Figure height in pixels
        show_baseline: Whether to show baseline reference line

    Returns:
        Plotly Figure object
    """
    fig = go.Figure()

    # Extract history data
    if state.history:
        iterations = [h["iteration"] for h in state.history]
        sse_values = [h["sse"] for h in state.history]
        best_values = [h.get("best_sse", h["sse"]) for h in state.history]

        # Main SSE line
        fig.add_trace(go.Scatter(
            x=iterations,
            y=sse_values,
            mode='lines+markers',
            name='Current SSE',
            line=dict(color=COLORS["sse_line"], width=2),
            marker=dict(size=4),
            hovertemplate='Iteration %{x}<br>SSE: %{y:,.0f}<extra></extra>',
        ))

        # Best SSE line (envelope)
        fig.add_trace(go.Scatter(
            x=iterations,
            y=best_values,
            mode='lines',
            name='Best SSE',
            line=dict(color=COLORS["best_point"], width=2, dash='dot'),
            hovertemplate='Iteration %{x}<br>Best: %{y:,.0f}<extra></extra>',
        ))

        # Mark best point
        if best_values:
            best_idx = best_values.index(min(best_values))
            fig.add_trace(go.Scatter(
                x=[iterations[best_idx]],
                y=[best_values[best_idx]],
                mode='markers',
                name='Best',
                marker=dict(
                    color=COLORS["best_point"],
                    size=12,
                    symbol='star',
                    line=dict(color='white', width=1),
                ),
                hovertemplate='Best at iteration %{x}<br>SSE: %{y:,.0f}<extra></extra>',
            ))

    # Baseline reference line
    if show_baseline and state.baseline_sse > 0:
        fig.add_hline(
            y=state.baseline_sse,
            line=dict(color=COLORS["baseline"], width=1, dash="dash"),
            annotation_text="Baseline",
            annotation_position="top right",
            annotation_font=dict(color=COLORS["baseline"], size=10),
        )

    # Layout
    fig.update_layout(
        height=height,
        margin=dict(l=60, r=20, t=30, b=40),
        paper_bgcolor=COLORS["paper"],
        plot_bgcolor=COLORS["background"],
        font=dict(color=COLORS["text"], family="Inter, sans-serif"),
        xaxis=dict(
            title="Iteration",
            gridcolor=COLORS["grid"],
            showgrid=True,
            zeroline=False,
        ),
        yaxis=dict(
            title="SSE",
            gridcolor=COLORS["grid"],
            showgrid=True,
            zeroline=False,
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor="rgba(0,0,0,0)",
        ),
        showlegend=True,
    )

    return fig


def create_method_comparison_figure(
    state: OptimizationState,
    height: int = 200,
) -> go.Figure:
    """Create figure comparing multiple optimization methods (explorer mode).

    Args:
        state: Current optimization state
        height: Figure height in pixels

    Returns:
        Plotly Figure object
    """
    fig = go.Figure()

    methods = list(state.method_results.keys())
    if not methods:
        return fig

    for method in methods:
        result = state.method_results[method]
        history = result.get("history", [])
        color = METHOD_COLORS.get(method, "#94a3b8")

        if history:
            iterations = [h["iteration"] for h in history]
            sse_values = [h["sse"] for h in history]

            fig.add_trace(go.Scatter(
                x=iterations,
                y=sse_values,
                mode='lines',
                name=method,
                line=dict(color=color, width=2),
                hovertemplate=f'{method}<br>Iter %{{x}}<br>SSE: %{{y:,.0f}}<extra></extra>',
            ))

    fig.update_layout(
        height=height,
        margin=dict(l=60, r=20, t=30, b=40),
        paper_bgcolor=COLORS["paper"],
        plot_bgcolor=COLORS["background"],
        font=dict(color=COLORS["text"]),
        xaxis=dict(title="Iteration", gridcolor=COLORS["grid"], showgrid=True),
        yaxis=dict(title="SSE", gridcolor=COLORS["grid"], showgrid=True),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
        ),
    )

    return fig


def render_optimization_stats_html(state: OptimizationState) -> str:
    """Render live statistics as HTML grid (matching exploration_tree.py style).

    Args:
        state: Current optimization state

    Returns:
        HTML string for stats display
    """
    elapsed = time.time() - state.start_time
    elapsed_str = f"{int(elapsed / 60)}:{int(elapsed % 60):02d}"

    # Format SSE values
    best_sse_str = f"{state.best_sse:,.0f}" if state.best_sse != float('inf') else "N/A"

    # Calculate improvement
    if state.baseline_sse > 0 and state.best_sse < float('inf'):
        improvement = ((state.baseline_sse - state.best_sse) / state.baseline_sse) * 100
        if improvement > 0:
            improv_str = f'<span style="color: #22c55e;">▲ {improvement:.1f}%</span>'
        elif improvement < 0:
            improv_str = f'<span style="color: #ef4444;">▼ {abs(improvement):.1f}%</span>'
        else:
            improv_str = "0%"
    else:
        improv_str = "N/A"

    # Footprint status
    if state.within_footprint:
        footprint_str = '<span style="color: #22c55e;">✓ Within</span>'
    else:
        footprint_str = '<span style="color: #ef4444;">✗ Exceeds</span>'

    # Progress
    progress_str = f"{state.current_iteration}/{state.max_iterations}"

    html = f"""
    <div style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; margin-top: 12px;">
        <div style="background: #1e293b; border-radius: 8px; padding: 12px; text-align: center;">
            <div style="font-size: 1.5rem; font-weight: 700; color: #3b82f6;">{progress_str}</div>
            <div style="font-size: 0.75rem; color: #94a3b8; margin-top: 4px;">Iteration</div>
        </div>
        <div style="background: #1e293b; border-radius: 8px; padding: 12px; text-align: center;">
            <div style="font-size: 1.5rem; font-weight: 700; color: #f59e0b;">{best_sse_str}</div>
            <div style="font-size: 0.75rem; color: #94a3b8; margin-top: 4px;">Best SSE</div>
        </div>
        <div style="background: #1e293b; border-radius: 8px; padding: 12px; text-align: center;">
            <div style="font-size: 1.5rem; font-weight: 700;">{improv_str}</div>
            <div style="font-size: 0.75rem; color: #94a3b8; margin-top: 4px;">Improvement</div>
        </div>
        <div style="background: #1e293b; border-radius: 8px; padding: 12px; text-align: center;">
            <div style="font-size: 1.25rem; font-weight: 700;">{footprint_str}</div>
            <div style="font-size: 0.75rem; color: #94a3b8; margin-top: 4px;">Footprint</div>
        </div>
        <div style="background: #1e293b; border-radius: 8px; padding: 12px; text-align: center;">
            <div style="font-size: 1.5rem; font-weight: 700; color: #e2e8f0;">{elapsed_str}</div>
            <div style="font-size: 0.75rem; color: #94a3b8; margin-top: 4px;">Elapsed</div>
        </div>
    </div>
    """
    return html


def render_explorer_stats_html(state: OptimizationState) -> str:
    """Render statistics for explorer mode with method comparison.

    Args:
        state: Current optimization state

    Returns:
        HTML string for stats display
    """
    elapsed = time.time() - state.start_time
    elapsed_str = f"{int(elapsed / 60)}:{int(elapsed % 60):02d}"

    # Phase indicator
    if state.phase == "grid_search":
        phase_str = f"Grid Search ({state.grid_points_evaluated} points)"
        phase_color = "#3b82f6"
    elif state.phase == "optimizing":
        phase_str = "Local Optimization"
        phase_color = "#f59e0b"
    else:
        phase_str = "Complete"
        phase_color = "#22c55e"

    # Best result across methods
    best_method = None
    best_sse = float('inf')
    for method, result in state.method_results.items():
        if result.get("best_sse", float('inf')) < best_sse:
            best_sse = result["best_sse"]
            best_method = method

    best_str = f"{best_sse:,.0f}" if best_sse != float('inf') else "N/A"
    method_str = best_method or "N/A"

    # Methods progress
    methods_complete = sum(1 for r in state.method_results.values() if r.get("status") == "complete")
    methods_total = len(state.method_results)
    methods_str = f"{methods_complete}/{methods_total}"

    html = f"""
    <div style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; margin-top: 12px;">
        <div style="background: #1e293b; border-radius: 8px; padding: 12px; text-align: center;">
            <div style="font-size: 1.1rem; font-weight: 700; color: {phase_color};">{phase_str}</div>
            <div style="font-size: 0.75rem; color: #94a3b8; margin-top: 4px;">Phase</div>
        </div>
        <div style="background: #1e293b; border-radius: 8px; padding: 12px; text-align: center;">
            <div style="font-size: 1.5rem; font-weight: 700; color: #3b82f6;">{methods_str}</div>
            <div style="font-size: 0.75rem; color: #94a3b8; margin-top: 4px;">Methods</div>
        </div>
        <div style="background: #1e293b; border-radius: 8px; padding: 12px; text-align: center;">
            <div style="font-size: 1.5rem; font-weight: 700; color: #f59e0b;">{best_str}</div>
            <div style="font-size: 0.75rem; color: #94a3b8; margin-top: 4px;">Best SSE</div>
        </div>
        <div style="background: #1e293b; border-radius: 8px; padding: 12px; text-align: center;">
            <div style="font-size: 1.25rem; font-weight: 700; color: #8b5cf6;">{method_str}</div>
            <div style="font-size: 0.75rem; color: #94a3b8; margin-top: 4px;">Best Method</div>
        </div>
        <div style="background: #1e293b; border-radius: 8px; padding: 12px; text-align: center;">
            <div style="font-size: 1.5rem; font-weight: 700; color: #e2e8f0;">{elapsed_str}</div>
            <div style="font-size: 0.75rem; color: #94a3b8; margin-top: 4px;">Elapsed</div>
        </div>
    </div>
    """
    return html


def render_parameter_changes_html(state: OptimizationState) -> str:
    """Render parameter changes compared to baseline.

    Args:
        state: Current optimization state

    Returns:
        HTML string showing parameter changes
    """
    if not state.baseline_params or not state.best_params:
        return "<p style='color: #94a3b8;'>No parameter data available</p>"

    rows = []
    for name, baseline_val in state.baseline_params.items():
        current_val = state.best_params.get(name, baseline_val)
        if baseline_val != 0:
            change_pct = ((current_val - baseline_val) / baseline_val) * 100
            if change_pct > 0.1:
                change_str = f'<span style="color: #22c55e;">↑ {change_pct:.1f}%</span>'
            elif change_pct < -0.1:
                change_str = f'<span style="color: #ef4444;">↓ {abs(change_pct):.1f}%</span>'
            else:
                change_str = '<span style="color: #94a3b8;">—</span>'
        else:
            change_str = '<span style="color: #94a3b8;">—</span>'

        rows.append(f"""
            <tr>
                <td style="padding: 4px 8px; color: #e2e8f0;">{name}</td>
                <td style="padding: 4px 8px; color: #f59e0b; text-align: right;">{current_val:.4f}</td>
                <td style="padding: 4px 8px; text-align: right;">{change_str}</td>
            </tr>
        """)

    html = f"""
    <div style="background: #1e293b; border-radius: 8px; padding: 12px;">
        <div style="font-weight: 600; color: #e2e8f0; margin-bottom: 8px;">Best Parameters</div>
        <table style="width: 100%; font-size: 0.85rem;">
            <thead>
                <tr style="color: #94a3b8;">
                    <th style="text-align: left; padding: 4px 8px;">Param</th>
                    <th style="text-align: right; padding: 4px 8px;">Value</th>
                    <th style="text-align: right; padding: 4px 8px;">Change</th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows)}
            </tbody>
        </table>
    </div>
    """
    return html
