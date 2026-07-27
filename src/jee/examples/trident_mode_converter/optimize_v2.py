#!/usr/bin/env python3
"""
Trident Optimizer V2 - Using the new GDSOptimizer framework.

This demonstrates the general-purpose optimization with automatic
footprint penalty enforcement.

Compared to optimize_trident.py:
- Uses GDSOptimizer class instead of manual scipy.optimize call
- Automatically enforces footprint constraints via penalty
- Cleaner, more reusable code
"""

from pathlib import Path

import numpy as np
import gdsfactory as gf

# Activate generic PDK (required for newer gdsfactory versions)
try:
    gf.get_active_pdk()
except ValueError:
    gf.gpdk.PDK.activate()

SCRIPT_DIR = Path(__file__).parent.resolve()

from jee.core import GDSOptimizer, OptimizerConfig


# ============================================================================
# Component Factory (same as original optimize_trident.py)
# ============================================================================

GRID = 0.002


def round_to_grid(val):
    return round(val / GRID) * GRID


@gf.cell
def tapered_s_bend(length=10.0, height=2.0, width_in=0.5, width_out=0.5, layer=(1, 0)):
    """S-bend with tapering width."""
    c = gf.Component()
    n_points = 201
    t = np.linspace(0, 1, n_points)
    x = length * t
    y = height * (1 - np.cos(np.pi * t)) / 2
    w = width_in + (width_out - width_in) * t
    dydx = (height * np.pi * np.sin(np.pi * t) / 2) / length
    angles = np.arctan(dydx)
    x_top = x - (w / 2) * np.sin(angles)
    y_top = y + (w / 2) * np.cos(angles)
    x_bot = x + (w / 2) * np.sin(angles)
    y_bot = y - (w / 2) * np.cos(angles)
    points = np.concatenate(
        [np.stack([x_top, y_top], axis=1), np.stack([x_bot, y_bot], axis=1)[::-1]]
    )
    c.add_polygon(points, layer=layer)
    c.add_port(name="o1", center=(0, 0), width=width_in, orientation=180, layer=layer)
    c.add_port(
        name="o2", center=(length, height), width=width_out, orientation=0, layer=layer
    )
    return c


def make_trident(params: dict) -> gf.Component:
    """
    Create trident mode converter from parameters.

    This is the factory function passed to GDSOptimizer.
    Takes a dict of parameters and returns a gf.Component.
    """
    c = gf.Component()
    layer = (1, 0)

    # Center taper
    center = c << gf.components.taper(
        length=params["mid_length"],
        width1=params["mid_width_in"],
        width2=params["mid_width_out"],
        layer=layer,
    )

    y_offset = (
        (params["mid_width_in"] / 2)
        + params["gap_start"]
        + (params["outer_width_in"] / 2)
    )

    # Top arm
    top_s = c << gf.components.taper(
        length=params["outer_length"],
        width1=params["outer_width_in"],
        width2=params["outer_width_out"],
        layer=layer,
    )
    top_s.movey(y_offset)

    top_b = c << tapered_s_bend(
        length=params["bend_length"],
        height=params["bend_height"],
        width_in=params["outer_width_out"],
        width_out=params["bend_width_end"],
        layer=layer,
    )
    top_b.connect("o1", top_s.ports["o2"])

    # Bottom arm (mirror)
    bot_s = c << gf.components.taper(
        length=params["outer_length"],
        width1=params["outer_width_in"],
        width2=params["outer_width_out"],
        layer=layer,
    )
    bot_s.movey(-y_offset)

    bot_b = c << tapered_s_bend(
        length=params["bend_length"],
        height=-params["bend_height"],
        width_in=params["outer_width_out"],
        width_out=params["bend_width_end"],
        layer=layer,
    )
    bot_b.connect("o1", bot_s.ports["o2"])

    return c


# ============================================================================
# Optimization Configuration
# ============================================================================

# Parameter names (order matters for optimization array)
PARAM_NAMES = [
    "mid_length",
    "mid_width_in",
    "mid_width_out",
    "outer_length",
    "outer_width_in",
    "outer_width_out",
    "gap_start",
    "bend_length",
    "bend_height",
    "bend_width_end",
]

# Parameter bounds
PARAM_BOUNDS = {
    "mid_length": (10.0, 22.0),
    "mid_width_in": (0.15, 0.30),
    "mid_width_out": (0.06, 0.15),
    "outer_length": (22.0, 28.0),
    "outer_width_in": (0.06, 0.15),
    "outer_width_out": (0.10, 0.20),
    "gap_start": (0.03, 0.10),
    "bend_length": (12.0, 18.0),
    "bend_height": (0.35, 0.65),
    "bend_width_end": (0.18, 0.35),
}

# Starting point (baseline with SSE ~89,854)
BASELINE = {
    "mid_length": 16.0,
    "mid_width_in": 0.222,
    "mid_width_out": 0.102,
    "outer_length": 24.8,
    "outer_width_in": 0.102,
    "outer_width_out": 0.142,
    "gap_start": 0.050,
    "bend_length": 15.2,
    "bend_height": 0.506,
    "bend_width_end": 0.264,
}


def main():
    """Run optimization using GDSOptimizer."""

    # Configuration
    config = OptimizerConfig(
        target_image=SCRIPT_DIR / "target.png",
        calibration_file=SCRIPT_DIR / "calibration.json",
        output_dir=SCRIPT_DIR / "results_v2",
        layer=1,
        datatype=0,
        flip_y=True,
        # Footprint penalty - the key new feature!
        footprint_penalty_enabled=True,
        footprint_penalty_weight=1.0,  # Same scale as SSE
        footprint_penalty_mode="match",  # "match" = penalize too big OR too small
        # Optimization settings
        method="Nelder-Mead",
        max_iterations=150,
        max_function_evals=250,
        grid_um=GRID,
        # Verbosity
        verbose=True,
        print_every=5,
    )

    # Create optimizer
    optimizer = GDSOptimizer(
        factory_fn=make_trident,
        param_names=PARAM_NAMES,
        param_bounds=PARAM_BOUNDS,
        baseline=BASELINE,
        config=config,
    )

    # Run optimization
    result = optimizer.run()

    # Summary
    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Baseline SSE: {result.baseline_sse:,.0f}")
    print(f"Best SSE: {result.best_sse:,.0f}")
    print(f"Footprint penalty: {result.best_footprint_penalty:,.0f}")
    print(f"Within footprint: {'YES' if result.within_footprint else 'NO'}")
    print(f"Improvement: {result.improvement_pct:.1f}%")
    print()
    print("This optimization used AUTOMATIC FOOTPRINT ENFORCEMENT.")
    print("Designs that exceed the target footprint are penalized.")


if __name__ == "__main__":
    main()
