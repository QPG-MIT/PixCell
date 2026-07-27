#!/usr/bin/env python3
"""
Trident Optimizer V3 - WITH POSITION PARAMETERS

Key insight: The trident has 5 disconnected shapes. The current optimization
only controls shapes, but forces all tapers to start at x=0. In the target
image, the center stub is clearly at a DIFFERENT x-position than the outer arms.

This version adds position parameters:
- center_x_offset: where center stub starts (can be different from outer arms)
- outer_x_offset: where outer arms start (relative to center)
- outer_y_offset: explicit y control (not derived from widths)

This should improve SSE by allowing fine-tuning of relative positions.
"""

from pathlib import Path

import numpy as np
import gdsfactory as gf

# Activate generic PDK
try:
    gf.get_active_pdk()
except ValueError:
    gf.gpdk.PDK.activate()

SCRIPT_DIR = Path(__file__).parent.resolve()

from jee.core import GDSOptimizer, OptimizerConfig


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
    c.add_port(name="o2", center=(length, height), width=width_out, orientation=0, layer=layer)
    return c


def make_trident_with_positions(params: dict) -> gf.Component:
    """
    Create trident with INDEPENDENT position control for each sub-component.

    Key difference from V2:
    - center_x_offset: X position of center stub (not forced to 0)
    - outer_x_offset: X position of outer arms (can differ from center)
    - outer_y_offset: Direct Y control (not derived from widths)
    """
    c = gf.Component()
    layer = (1, 0)

    # =========================================================================
    # CENTER STUB - position now controllable
    # =========================================================================
    center = c << gf.components.taper(
        length=params["mid_length"],
        width1=params["mid_width_in"],
        width2=params["mid_width_out"],
        layer=layer,
    )
    # NEW: Center can be offset in X (not forced to 0)
    center.move((params["center_x_offset"], 0))

    # =========================================================================
    # TOP ARM - independent X and Y positioning
    # =========================================================================
    top_s = c << gf.components.taper(
        length=params["outer_length"],
        width1=params["outer_width_in"],
        width2=params["outer_width_out"],
        layer=layer,
    )
    # NEW: Both X and Y are now independent parameters
    top_s.move((params["outer_x_offset"], params["outer_y_offset"]))

    top_b = c << tapered_s_bend(
        length=params["bend_length"],
        height=params["bend_height"],
        width_in=params["outer_width_out"],
        width_out=params["bend_width_end"],
        layer=layer,
    )
    top_b.connect("o1", top_s.ports["o2"])

    # =========================================================================
    # BOTTOM ARM - mirrored Y, same X offset as top
    # =========================================================================
    bot_s = c << gf.components.taper(
        length=params["outer_length"],
        width1=params["outer_width_in"],
        width2=params["outer_width_out"],
        layer=layer,
    )
    # NEW: X same as top, Y mirrored
    bot_s.move((params["outer_x_offset"], -params["outer_y_offset"]))

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
# Parameters: SHAPE + POSITION
# ============================================================================

PARAM_NAMES = [
    # Shape parameters (same as V2)
    "mid_length",
    "mid_width_in",
    "mid_width_out",
    "outer_length",
    "outer_width_in",
    "outer_width_out",
    "bend_length",
    "bend_height",
    "bend_width_end",

    # POSITION parameters (NEW!)
    "center_x_offset",   # Where center stub starts in X
    "outer_x_offset",    # Where outer arms start in X (can differ from center)
    "outer_y_offset",    # Y distance from center (now independent, not derived)
]

# Removed gap_start since outer_y_offset replaces its function
# but provides direct control instead of derived positioning

PARAM_BOUNDS = {
    # Shape bounds (same as before)
    "mid_length": (10.0, 22.0),
    "mid_width_in": (0.15, 0.35),
    "mid_width_out": (0.06, 0.15),
    "outer_length": (20.0, 30.0),
    "outer_width_in": (0.06, 0.20),
    "outer_width_out": (0.10, 0.25),
    "bend_length": (10.0, 20.0),
    "bend_height": (0.30, 0.70),
    "bend_width_end": (0.15, 0.40),

    # POSITION bounds (NEW!)
    # Allow center stub to shift in X by up to ±5 μm
    "center_x_offset": (-2.0, 5.0),

    # Allow outer arms to start at different X than center
    "outer_x_offset": (-2.0, 3.0),

    # Y offset for outer arms (replaces derived y_offset)
    # This is the distance from centerline to outer arm centerline
    "outer_y_offset": (0.15, 0.60),
}

# Baseline - initial guess
BASELINE = {
    # Shape (from best V4 result)
    "mid_length": 14.372,
    "mid_width_in": 0.3,
    "mid_width_out": 0.082,
    "outer_length": 25.868,
    "outer_width_in": 0.102,
    "outer_width_out": 0.2,
    "bend_length": 12.742,
    "bend_height": 0.49,
    "bend_width_end": 0.246,

    # POSITION (NEW!) - initial guess based on image inspection
    # The center stub appears shifted right compared to outer arms
    "center_x_offset": 0.0,    # Start at origin (will be optimized)
    "outer_x_offset": 0.0,     # Outer arms also at origin initially
    "outer_y_offset": 0.35,    # Approximate from original gap_start calculation
}


def main():
    """Run optimization with position parameters."""

    print("=" * 70)
    print("TRIDENT V3: OPTIMIZATION WITH POSITION PARAMETERS")
    print("=" * 70)
    print()
    print("Key insight: The trident has 5 disconnected shapes.")
    print("V2 forced all tapers to start at x=0, but in the target image,")
    print("the center stub is at a DIFFERENT x-position than the outer arms.")
    print()
    print(f"Total parameters: {len(PARAM_NAMES)}")
    print(f"  Shape parameters: 9")
    print(f"  Position parameters: 3 (center_x, outer_x, outer_y)")
    print()

    # Configuration
    config = OptimizerConfig(
        target_image=SCRIPT_DIR / "target.png",
        calibration_file=SCRIPT_DIR / "calibration.json",
        output_dir=SCRIPT_DIR / "results_v3_positions",
        layer=1,
        datatype=0,
        flip_y=True,
        footprint_penalty_enabled=False,  # Disable to compare pure SSE
        method="Nelder-Mead",
        max_iterations=200,  # More iterations for larger param space
        max_function_evals=350,
        grid_um=GRID,
        verbose=True,
        print_every=5,
    )

    # Create optimizer
    optimizer = GDSOptimizer(
        factory_fn=make_trident_with_positions,
        param_names=PARAM_NAMES,
        param_bounds=PARAM_BOUNDS,
        baseline=BASELINE,
        config=config,
    )

    # Run optimization
    result = optimizer.run()

    # Summary
    print()
    print("=" * 70)
    print("RESULTS: V3 WITH POSITION OPTIMIZATION")
    print("=" * 70)
    print(f"Baseline SSE: {result.baseline_sse:,.0f}")
    print(f"Best SSE: {result.best_sse:,.0f}")
    print(f"Improvement: {result.improvement_pct:.1f}%")
    print()

    if result.best_params:
        print("Position parameters found:")
        print(f"  center_x_offset: {result.best_params['center_x_offset']:.3f} μm")
        print(f"  outer_x_offset:  {result.best_params['outer_x_offset']:.3f} μm")
        print(f"  outer_y_offset:  {result.best_params['outer_y_offset']:.3f} μm")
        print()

        x_diff = result.best_params['center_x_offset'] - result.best_params['outer_x_offset']
        print(f"X difference (center vs outer): {x_diff:.3f} μm")

        if abs(x_diff) > 0.1:
            print("  → Significant X offset between center and outer arms!")
            print("  → This confirms position optimization is valuable.")

    print()
    print("COMPARISON:")
    print("  V2 (shape-only):     SSE ~32,304 (64% improvement)")
    print(f"  V3 (shape+position): SSE {result.best_sse:,.0f} ({result.improvement_pct:.1f}% improvement)")

    if result.best_sse < 32304:
        delta = 32304 - result.best_sse
        pct_better = (delta / 32304) * 100
        print(f"  → V3 is {pct_better:.1f}% better than V2!")
    else:
        print("  → Run this to compare actual results")


if __name__ == "__main__":
    main()
