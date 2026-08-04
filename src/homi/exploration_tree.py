"""
Exploration Tree Visualization Module

Provides real-time tree visualization for Phase 1 and Phase 2 seed exploration.
Displays seeds as nodes branching from each phase, with turns as child nodes,
color-coded by status and quality metrics.
"""

import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

import plotly.graph_objects as go


# Status constants
STATUS_PENDING = "pending"
STATUS_RUNNING = "running"
STATUS_COMPLETE = "complete"
STATUS_FAILED = "failed"

# Node type constants
NODE_PHASE = "phase"
NODE_SEED = "seed"
NODE_TURN = "turn"

# Color scheme (dark theme compatible)
STATUS_COLORS = {
    STATUS_PENDING: "#64748b",   # Slate gray
    STATUS_RUNNING: "#f59e0b",   # Amber
    STATUS_COMPLETE: "#22c55e",  # Green
    STATUS_FAILED: "#ef4444",    # Red
}

# Quality color gradient (for completed nodes based on metrics)
QUALITY_COLORS = {
    "excellent": "#22c55e",  # Green
    "good": "#84cc16",       # Lime
    "fair": "#f59e0b",       # Amber
    "poor": "#f97316",       # Orange
    "bad": "#ef4444",        # Red
}


@dataclass
class TreeNode:
    """Represents a node in the exploration tree."""
    id: str                          # Unique identifier (e.g., "phase1", "seed_1333", "seed_1333_turn1")
    parent_id: Optional[str]         # Parent node ID
    node_type: str                   # "phase", "seed", "turn"
    label: str                       # Display label
    status: str = STATUS_PENDING     # "pending", "running", "complete", "failed"
    metrics: Optional[Dict[str, Any]] = None   # IoU, SSE, Dice scores
    seed_value: Optional[int] = None  # Actual seed number
    turn_number: Optional[int] = None # Turn number for turn nodes
    run_id: Optional[int] = None      # Run ID from exploration
    timestamp: Optional[float] = None # When status changed

    # Layout coordinates (computed by layout algorithm)
    x: float = 0.0
    y: float = 0.0


@dataclass
class ExplorationTreeState:
    """Complete state of the exploration tree."""
    nodes: Dict[str, TreeNode] = field(default_factory=dict)
    phase: str = "phase1"            # Current phase: "phase1" or "phase2"
    config: Dict[str, Any] = field(default_factory=dict)  # total_seeds, base_seed, etc.
    start_time: float = field(default_factory=time.time)

    # Summary statistics (updated as exploration progresses)
    total_seeds: int = 0
    completed_seeds: int = 0
    successful_seeds: int = 0
    failed_seeds: int = 0
    best_sse: float = float('inf')
    best_iou: float = 0.0
    best_seed: Optional[int] = None

    # For debouncing updates
    last_render_time: float = 0.0
    update_counter: int = 0


def get_quality_color(metrics: Optional[Dict[str, Any]], metric_type: str = "sse") -> str:
    """Get color based on metric quality.

    Args:
        metrics: Dictionary containing SSE, IoU, Dice values
        metric_type: Which metric to use for coloring ("sse" or "iou")

    Returns:
        Hex color string
    """
    if not metrics:
        return STATUS_COLORS[STATUS_PENDING]

    if metric_type == "sse":
        sse = metrics.get("SSE", metrics.get("sse", float('inf')))
        if sse == float('inf'):
            return STATUS_COLORS[STATUS_PENDING]
        if sse < 100000:
            return QUALITY_COLORS["excellent"]
        elif sse < 200000:
            return QUALITY_COLORS["good"]
        elif sse < 300000:
            return QUALITY_COLORS["fair"]
        elif sse < 400000:
            return QUALITY_COLORS["poor"]
        else:
            return QUALITY_COLORS["bad"]

    elif metric_type == "iou":
        iou = metrics.get("IoU", metrics.get("iou", 0))
        if iou > 0.7:
            return QUALITY_COLORS["excellent"]
        elif iou > 0.5:
            return QUALITY_COLORS["good"]
        elif iou > 0.3:
            return QUALITY_COLORS["fair"]
        elif iou > 0.15:
            return QUALITY_COLORS["poor"]
        else:
            return QUALITY_COLORS["bad"]

    return STATUS_COLORS[STATUS_PENDING]


def compute_tree_layout(state: ExplorationTreeState) -> Dict[str, Tuple[float, float]]:
    """Compute x, y positions for all nodes using hierarchical layout.

    Args:
        state: Current exploration tree state

    Returns:
        Dictionary mapping node IDs to (x, y) coordinates
    """
    if not state.nodes:
        return {}

    pos = {}

    # Group nodes by type
    phase_nodes = [n for n in state.nodes.values() if n.node_type == NODE_PHASE]
    seed_nodes = sorted(
        [n for n in state.nodes.values() if n.node_type == NODE_SEED],
        key=lambda n: (n.run_id or 0, n.seed_value or 0)
    )
    turn_nodes = [n for n in state.nodes.values() if n.node_type == NODE_TURN]

    # Y levels: phase=2, seeds=1, turns=0
    phase_y = 2.0
    seed_y = 1.0
    turn_y = 0.0

    # Position phase node(s) at top center
    for i, phase in enumerate(phase_nodes):
        pos[phase.id] = (i * 2.0, phase_y)

    # Calculate seed spacing based on count
    num_seeds = len(seed_nodes)
    if num_seeds > 0:
        # Use wider spacing for fewer seeds, tighter for many
        if num_seeds <= 5:
            seed_spacing = 2.0
        elif num_seeds <= 13:
            seed_spacing = 1.5
        elif num_seeds <= 25:
            seed_spacing = 1.0
        else:
            seed_spacing = 0.7

        # Center seeds around x=0
        total_width = (num_seeds - 1) * seed_spacing
        start_x = -total_width / 2

        for i, seed in enumerate(seed_nodes):
            x = start_x + i * seed_spacing
            pos[seed.id] = (x, seed_y)

    # Position turn nodes below their parent seeds
    turn_spacing = 0.3
    for seed in seed_nodes:
        if seed.id not in pos:
            continue
        seed_x, _ = pos[seed.id]

        # Find turns for this seed
        seed_turns = sorted(
            [t for t in turn_nodes if t.parent_id == seed.id],
            key=lambda t: t.turn_number or 0
        )

        if seed_turns:
            num_turns = len(seed_turns)
            turn_width = (num_turns - 1) * turn_spacing
            start_turn_x = seed_x - turn_width / 2

            for j, turn in enumerate(seed_turns):
                tx = start_turn_x + j * turn_spacing
                pos[turn.id] = (tx, turn_y)

    return pos


def create_tree_figure(
    state: ExplorationTreeState,
    height: int = 400,
    show_metrics: bool = True,
    color_by: str = "status"  # "status" or "quality"
) -> go.Figure:
    """Create Plotly figure for the exploration tree.

    Args:
        state: Current exploration tree state
        height: Figure height in pixels
        show_metrics: Whether to show metrics in hover text
        color_by: How to color nodes - "status" or "quality" (based on SSE)

    Returns:
        Plotly Figure object
    """
    if not state.nodes:
        # Return empty figure with message
        fig = go.Figure()
        fig.add_annotation(
            text="Waiting for exploration to start...",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=16, color="#94a3b8")
        )
        fig.update_layout(
            plot_bgcolor='#0f172a',
            paper_bgcolor='#0f172a',
            height=height,
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
        )
        return fig

    # Compute layout
    positions = compute_tree_layout(state)

    # Create figure
    fig = go.Figure()

    # Draw edges (lines connecting nodes)
    edge_x = []
    edge_y = []
    for node in state.nodes.values():
        if node.parent_id and node.parent_id in positions and node.id in positions:
            px, py = positions[node.parent_id]
            nx, ny = positions[node.id]
            edge_x.extend([px, nx, None])
            edge_y.extend([py, ny, None])

    if edge_x:
        fig.add_trace(go.Scatter(
            x=edge_x, y=edge_y,
            mode='lines',
            line=dict(color='#475569', width=1.5),
            hoverinfo='none',
            showlegend=False
        ))

    # Group nodes by status for legend
    if color_by == "status":
        for status, color in STATUS_COLORS.items():
            status_nodes = [n for n in state.nodes.values() if n.status == status and n.id in positions]
            if not status_nodes:
                continue

            x_vals = [positions[n.id][0] for n in status_nodes]
            y_vals = [positions[n.id][1] for n in status_nodes]

            # Build hover text
            hover_texts = []
            for n in status_nodes:
                text = f"<b>{n.label}</b><br>Status: {n.status.capitalize()}"
                if show_metrics and n.metrics:
                    sse = n.metrics.get("SSE", n.metrics.get("sse"))
                    iou = n.metrics.get("IoU", n.metrics.get("iou"))
                    if sse is not None:
                        text += f"<br>SSE: {sse:,.0f}" if sse != float('inf') else "<br>SSE: N/A"
                    if iou is not None:
                        text += f"<br>IoU: {iou:.4f}"
                hover_texts.append(text)

            # Size based on node type
            sizes = []
            for n in status_nodes:
                if n.node_type == NODE_PHASE:
                    sizes.append(35)
                elif n.node_type == NODE_SEED:
                    sizes.append(22)
                else:
                    sizes.append(14)

            # Labels (only show for phase and seed nodes)
            labels = []
            for n in status_nodes:
                if n.node_type == NODE_PHASE:
                    labels.append(n.label)
                elif n.node_type == NODE_SEED:
                    # Show seed number or run ID
                    if n.seed_value:
                        labels.append(str(n.seed_value))
                    elif n.run_id is not None:
                        labels.append(f"R{n.run_id}")
                    else:
                        labels.append("")
                else:
                    labels.append(f"T{n.turn_number}" if n.turn_number else "")

            fig.add_trace(go.Scatter(
                x=x_vals, y=y_vals,
                mode='markers+text',
                marker=dict(
                    size=sizes,
                    color=color,
                    line=dict(width=2, color='#1e293b'),
                    symbol='circle'
                ),
                text=labels,
                textposition='top center',
                textfont=dict(size=9, color='#e2e8f0'),
                hovertemplate='%{customdata}<extra></extra>',
                customdata=hover_texts,
                name=status.capitalize(),
                showlegend=True
            ))

    else:  # color_by == "quality"
        # Color completed nodes by quality, others by status
        for node in state.nodes.values():
            if node.id not in positions:
                continue

            x, y = positions[node.id]

            if node.status == STATUS_COMPLETE and node.metrics:
                color = get_quality_color(node.metrics, "sse")
            else:
                color = STATUS_COLORS.get(node.status, STATUS_COLORS[STATUS_PENDING])

            # Size based on node type
            if node.node_type == NODE_PHASE:
                size = 35
            elif node.node_type == NODE_SEED:
                size = 22
            else:
                size = 14

            # Label
            if node.node_type == NODE_PHASE:
                label = node.label
            elif node.node_type == NODE_SEED:
                label = str(node.seed_value) if node.seed_value else f"R{node.run_id}"
            else:
                label = f"T{node.turn_number}" if node.turn_number else ""

            # Hover text
            hover_text = f"<b>{node.label}</b><br>Status: {node.status.capitalize()}"
            if show_metrics and node.metrics:
                sse = node.metrics.get("SSE", node.metrics.get("sse"))
                iou = node.metrics.get("IoU", node.metrics.get("iou"))
                if sse is not None:
                    hover_text += f"<br>SSE: {sse:,.0f}" if sse != float('inf') else "<br>SSE: N/A"
                if iou is not None:
                    hover_text += f"<br>IoU: {iou:.4f}"

            fig.add_trace(go.Scatter(
                x=[x], y=[y],
                mode='markers+text',
                marker=dict(
                    size=size,
                    color=color,
                    line=dict(width=2, color='#1e293b'),
                    symbol='circle'
                ),
                text=[label],
                textposition='top center',
                textfont=dict(size=9, color='#e2e8f0'),
                hovertemplate=f'{hover_text}<extra></extra>',
                showlegend=False
            ))

    # Update layout
    fig.update_layout(
        showlegend=True if color_by == "status" else False,
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='center',
            x=0.5,
            font=dict(color='#e2e8f0', size=11),
            bgcolor='rgba(0,0,0,0)'
        ),
        xaxis=dict(
            showgrid=False,
            zeroline=False,
            showticklabels=False,
            range=None  # Auto-range
        ),
        yaxis=dict(
            showgrid=False,
            zeroline=False,
            showticklabels=False,
            range=[-0.5, 2.5]
        ),
        plot_bgcolor='#0f172a',
        paper_bgcolor='#0f172a',
        height=height,
        margin=dict(l=20, r=20, t=50, b=20),
        hovermode='closest'
    )

    return fig


def parse_exploration_log_line(line: str) -> Optional[Dict[str, Any]]:
    """Parse a log line from exploration subprocess into structured data.

    Args:
        line: Raw log line from subprocess

    Returns:
        Structured data dict or None if line doesn't match patterns
    """
    if not line:
        return None

    # Pattern: [Seed 1333] Starting (seed=1333) or [Run 0] Starting
    seed_start = re.search(r'\[(?:Seed\s+(\d+)|Run\s+(\d+))\]\s+Starting', line)
    if seed_start:
        seed = seed_start.group(1)
        run_id = seed_start.group(2)
        return {
            "type": "seed_start",
            "seed": int(seed) if seed else None,
            "run_id": int(run_id) if run_id else None
        }

    # Pattern: [Seed 1333] Turn 1 SUCCESS (attempt 1)
    turn_success = re.search(r'\[(?:Seed\s+(\d+)|Run\s+(\d+))\]\s+Turn\s+(\d+)\s+SUCCESS', line)
    if turn_success:
        seed = turn_success.group(1)
        run_id = turn_success.group(2)
        turn = turn_success.group(3)
        return {
            "type": "turn_complete",
            "seed": int(seed) if seed else None,
            "run_id": int(run_id) if run_id else None,
            "turn": int(turn),
            "success": True
        }

    # Pattern: [Seed 1333] Turn 1 FAILED after X attempts
    turn_failed = re.search(r'\[(?:Seed\s+(\d+)|Run\s+(\d+))\]\s+Turn\s+(\d+)\s+FAILED', line)
    if turn_failed:
        seed = turn_failed.group(1)
        run_id = turn_failed.group(2)
        turn = turn_failed.group(3)
        return {
            "type": "turn_complete",
            "seed": int(seed) if seed else None,
            "run_id": int(run_id) if run_id else None,
            "turn": int(turn),
            "success": False
        }

    # Pattern: [Seed 1333] Turn 1 metrics: SSE=125000, IoU=0.4500
    # or: SSE=125000.0, IoU=0.4500, Dice=0.6200
    metrics_match = re.search(
        r'\[(?:Seed\s+(\d+)|Run\s+(\d+))\]\s+Turn\s+(\d+)\s+metrics:.*?'
        r'SSE[=:]\s*(\d+\.?\d*)',
        line
    )
    if metrics_match:
        seed = metrics_match.group(1)
        run_id = metrics_match.group(2)
        turn = metrics_match.group(3)
        sse = metrics_match.group(4)

        # Also try to extract IoU
        iou_match = re.search(r'IoU[=:]\s*(\d+\.?\d*)', line)
        iou = float(iou_match.group(1)) if iou_match else None

        # And Dice
        dice_match = re.search(r'Dice[=:]\s*(\d+\.?\d*)', line)
        dice = float(dice_match.group(1)) if dice_match else None

        return {
            "type": "metrics",
            "seed": int(seed) if seed else None,
            "run_id": int(run_id) if run_id else None,
            "turn": int(turn),
            "metrics": {
                "SSE": float(sse),
                "IoU": iou,
                "Dice": dice
            }
        }

    # Pattern: Run X complete or Seed complete
    seed_complete = re.search(r'\[(?:Seed\s+(\d+)|Run\s+(\d+))\]\s+(?:Complete|Finished)', line, re.IGNORECASE)
    if seed_complete:
        seed = seed_complete.group(1)
        run_id = seed_complete.group(2)
        return {
            "type": "seed_complete",
            "seed": int(seed) if seed else None,
            "run_id": int(run_id) if run_id else None
        }

    return None


def update_tree_from_callback(state: ExplorationTreeState, data: Dict[str, Any]) -> bool:
    """Update tree state from callback data.

    Args:
        state: Current exploration tree state (modified in place)
        data: Callback data (either structured or log message)

    Returns:
        True if state was updated, False otherwise
    """
    # Handle raw log message
    if data.get("type") == "log":
        message = data.get("message", "")
        parsed = parse_exploration_log_line(message)
        if not parsed:
            return False
        data = parsed

    event_type = data.get("type")
    seed = data.get("seed")
    run_id = data.get("run_id")
    turn = data.get("turn")

    # Create seed identifier
    if seed is not None:
        seed_id = f"seed_{seed}"
        seed_label = f"Seed {seed}"
    elif run_id is not None:
        seed_id = f"run_{run_id}"
        seed_label = f"Run {run_id}"
    else:
        return False

    updated = False

    if event_type == "seed_start":
        # Create seed node if it doesn't exist
        if seed_id not in state.nodes:
            parent_id = f"{state.phase}"
            state.nodes[seed_id] = TreeNode(
                id=seed_id,
                parent_id=parent_id,
                node_type=NODE_SEED,
                label=seed_label,
                status=STATUS_RUNNING,
                seed_value=seed,
                run_id=run_id,
                timestamp=time.time()
            )
            updated = True
        else:
            # Update status to running
            state.nodes[seed_id].status = STATUS_RUNNING
            updated = True

    elif event_type == "turn_complete":
        # Ensure seed node exists
        if seed_id not in state.nodes:
            parent_id = f"{state.phase}"
            state.nodes[seed_id] = TreeNode(
                id=seed_id,
                parent_id=parent_id,
                node_type=NODE_SEED,
                label=seed_label,
                status=STATUS_RUNNING,
                seed_value=seed,
                run_id=run_id,
                timestamp=time.time()
            )

        # Create turn node
        turn_id = f"{seed_id}_turn{turn}"
        success = data.get("success", True)

        state.nodes[turn_id] = TreeNode(
            id=turn_id,
            parent_id=seed_id,
            node_type=NODE_TURN,
            label=f"Turn {turn}",
            status=STATUS_COMPLETE if success else STATUS_FAILED,
            turn_number=turn,
            seed_value=seed,
            run_id=run_id,
            timestamp=time.time()
        )
        updated = True

    elif event_type == "metrics":
        # Update turn node with metrics
        turn_id = f"{seed_id}_turn{turn}"
        if turn_id in state.nodes:
            state.nodes[turn_id].metrics = data.get("metrics")
            updated = True

        # Also update seed node with best metrics
        if seed_id in state.nodes:
            node = state.nodes[seed_id]
            metrics = data.get("metrics", {})

            if node.metrics is None:
                node.metrics = metrics
            else:
                # Keep best metrics
                current_sse = node.metrics.get("SSE", float('inf'))
                new_sse = metrics.get("SSE", float('inf'))
                if new_sse < current_sse:
                    node.metrics = metrics

            # Update global best
            sse = metrics.get("SSE", float('inf'))
            iou = metrics.get("IoU", 0)

            if sse < state.best_sse:
                state.best_sse = sse
                state.best_seed = seed or run_id

            if iou > state.best_iou:
                state.best_iou = iou

            updated = True

    elif event_type == "seed_complete":
        # Mark seed as complete
        if seed_id in state.nodes:
            node = state.nodes[seed_id]

            # Check if any turns failed
            turn_nodes = [n for n in state.nodes.values()
                         if n.parent_id == seed_id and n.node_type == NODE_TURN]
            failed_turns = [n for n in turn_nodes if n.status == STATUS_FAILED]

            if failed_turns and len(failed_turns) == len(turn_nodes):
                node.status = STATUS_FAILED
                state.failed_seeds += 1
            else:
                node.status = STATUS_COMPLETE
                state.successful_seeds += 1

            state.completed_seeds += 1
            updated = True

    if updated:
        state.update_counter += 1

    return updated


def initialize_tree_state(
    phase: str,
    total_seeds: int,
    base_seed: int,
    seed_range: int,
    **kwargs
) -> ExplorationTreeState:
    """Initialize a new exploration tree state.

    Args:
        phase: "phase1" or "phase2"
        total_seeds: Total number of seeds to explore
        base_seed: Base seed value
        seed_range: Range around base seed (+/-)
        **kwargs: Additional config values

    Returns:
        Initialized ExplorationTreeState
    """
    state = ExplorationTreeState(
        nodes={},
        phase=phase,
        config={
            "total_seeds": total_seeds,
            "base_seed": base_seed,
            "seed_range": seed_range,
            **kwargs
        },
        start_time=time.time(),
        total_seeds=total_seeds
    )

    # Add phase root node
    phase_label = "Phase 1" if phase == "phase1" else "Phase 2"
    state.nodes[phase] = TreeNode(
        id=phase,
        parent_id=None,
        node_type=NODE_PHASE,
        label=phase_label,
        status=STATUS_RUNNING,
        timestamp=time.time()
    )

    return state


def render_tree_stats_html(state: ExplorationTreeState) -> str:
    """Render live statistics as HTML.

    Args:
        state: Current exploration tree state

    Returns:
        HTML string for stats display
    """
    elapsed = time.time() - state.start_time
    elapsed_str = f"{int(elapsed // 60)}:{int(elapsed % 60):02d}"

    sse_str = f"{state.best_sse:,.0f}" if state.best_sse != float('inf') else "N/A"
    iou_str = f"{state.best_iou:.4f}" if state.best_iou > 0 else "N/A"

    html = f"""
    <div style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; margin-top: 12px;">
        <div style="background: #1e293b; border-radius: 8px; padding: 12px; text-align: center;">
            <div style="font-size: 1.5rem; font-weight: 700; color: #3b82f6;">{state.completed_seeds}/{state.total_seeds}</div>
            <div style="font-size: 0.75rem; color: #94a3b8; margin-top: 4px;">Seeds</div>
        </div>
        <div style="background: #1e293b; border-radius: 8px; padding: 12px; text-align: center;">
            <div style="font-size: 1.5rem; font-weight: 700; color: #22c55e;">{state.successful_seeds}</div>
            <div style="font-size: 0.75rem; color: #94a3b8; margin-top: 4px;">Successful</div>
        </div>
        <div style="background: #1e293b; border-radius: 8px; padding: 12px; text-align: center;">
            <div style="font-size: 1.5rem; font-weight: 700; color: #f59e0b;">{sse_str}</div>
            <div style="font-size: 0.75rem; color: #94a3b8; margin-top: 4px;">Best SSE</div>
        </div>
        <div style="background: #1e293b; border-radius: 8px; padding: 12px; text-align: center;">
            <div style="font-size: 1.5rem; font-weight: 700; color: #8b5cf6;">{iou_str}</div>
            <div style="font-size: 0.75rem; color: #94a3b8; margin-top: 4px;">Best IoU</div>
        </div>
        <div style="background: #1e293b; border-radius: 8px; padding: 12px; text-align: center;">
            <div style="font-size: 1.5rem; font-weight: 700; color: #e2e8f0;">{elapsed_str}</div>
            <div style="font-size: 0.75rem; color: #94a3b8; margin-top: 4px;">Elapsed</div>
        </div>
    </div>
    """
    return html
