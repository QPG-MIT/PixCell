#!/usr/bin/env python3
"""
Multi-Component Optimizer with Position Parameters

This demonstrates optimizing BOTH component shapes AND positions.
Key insight: For multi-component devices, position optimization can
significantly improve results since calibration-based extraction
introduces positional errors.

Parameters optimized:
- Shape params: length, width, gap, etc. (per component)
- Position params: x_offset, y_offset (per component)
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


# ============================================================================
# Component Factories (individual sub-components)
# ============================================================================

def make_left_branch(width_in, width_out, length, bend_height):
    """Left curved branch: taper + S-bend."""
    c = gf.Component()
    layer = (1, 0)

    # Taper
    taper = c << gf.components.taper(
        length=length * 0.6,
        width1=width_in,
        width2=width_out,
        layer=layer,
    )

    # S-bend
    bend = c << gf.components.bend_s(
        size=(length * 0.4, bend_height),
        cross_section=gf.cross_section.strip(width=width_out, layer=layer),
    )
    bend.connect("o1", taper.ports["o2"])

    return c


def make_center_stub(width_in, width_out, length):
    """Center stub: simple taper."""
    c = gf.Component()
    layer = (1, 0)

    taper = c << gf.components.taper(
        length=length,
        width1=width_in,
        width2=width_out,
        layer=layer,
    )

    return c


def make_right_branch(width_in, width_out, length, bend_height):
    """Right curved branch: taper + S-bend (mirrored)."""
    c = gf.Component()
    layer = (1, 0)

    # Taper
    taper = c << gf.components.taper(
        length=length * 0.6,
        width1=width_in,
        width2=width_out,
        layer=layer,
    )

    # S-bend (negative height for downward curve)
    bend = c << gf.components.bend_s(
        size=(length * 0.4, -bend_height),
        cross_section=gf.cross_section.strip(width=width_out, layer=layer),
    )
    bend.connect("o1", taper.ports["o2"])

    return c


# ============================================================================
# Multi-Component Assembly with Position Optimization
# ============================================================================

def make_device_with_positions(params: dict) -> gf.Component:
    """
    Assemble multi-component device with optimizable positions.

    This is the KEY INNOVATION: positions are now optimization parameters,
    not fixed values extracted from calibration.

    Parameters include:
    - Shape params for each component
    - Position params (x_offset, y_offset) for components 2 and 3
      (component 1 is the reference at origin)
    """
    c = gf.Component()

    # =========================================================================
    # Component 1: Left branch (reference - fixed at origin)
    # =========================================================================
    comp1 = make_left_branch(
        width_in=params["comp1_width_in"],
        width_out=params["comp1_width_out"],
        length=params["comp1_length"],
        bend_height=params["comp1_bend_height"],
    )
    ref1 = c << comp1
    # Component 1 stays at origin (reference point)

    # =========================================================================
    # Component 2: Center stub (position optimized relative to comp1)
    # =========================================================================
    comp2 = make_center_stub(
        width_in=params["comp2_width_in"],
        width_out=params["comp2_width_out"],
        length=params["comp2_length"],
    )
    ref2 = c << comp2

    # POSITION OPTIMIZATION: x and y offsets are parameters!
    ref2.move((params["comp2_x_offset"], params["comp2_y_offset"]))

    # =========================================================================
    # Component 3: Right branch (position optimized relative to comp1)
    # =========================================================================
    comp3 = make_right_branch(
        width_in=params["comp3_width_in"],
        width_out=params["comp3_width_out"],
        length=params["comp3_length"],
        bend_height=params["comp3_bend_height"],
    )
    ref3 = c << comp3

    # POSITION OPTIMIZATION: x and y offsets are parameters!
    ref3.move((params["comp3_x_offset"], params["comp3_y_offset"]))

    return c


# ============================================================================
# Parameter Configuration (SHAPE + POSITION)
# ============================================================================

# Parameter names - now includes position params!
PARAM_NAMES = [
    # Component 1 (shape only - position fixed at origin)
    "comp1_width_in",
    "comp1_width_out",
    "comp1_length",
    "comp1_bend_height",

    # Component 2 (shape + position)
    "comp2_width_in",
    "comp2_width_out",
    "comp2_length",
    "comp2_x_offset",      # <-- POSITION PARAM
    "comp2_y_offset",      # <-- POSITION PARAM

    # Component 3 (shape + position)
    "comp3_width_in",
    "comp3_width_out",
    "comp3_length",
    "comp3_bend_height",
    "comp3_x_offset",      # <-- POSITION PARAM
    "comp3_y_offset",      # <-- POSITION PARAM
]

# Parameter bounds
PARAM_BOUNDS = {
    # Component 1 shapes
    "comp1_width_in": (0.3, 0.8),
    "comp1_width_out": (0.2, 0.5),
    "comp1_length": (15.0, 25.0),
    "comp1_bend_height": (0.3, 0.8),

    # Component 2 shapes
    "comp2_width_in": (0.2, 0.5),
    "comp2_width_out": (0.1, 0.3),
    "comp2_length": (5.0, 12.0),

    # Component 2 POSITIONS - allow ±2μm adjustment from baseline
    "comp2_x_offset": (6.0, 10.0),   # Roughly where comp2 should be
    "comp2_y_offset": (-0.5, 0.5),   # Allow vertical adjustment

    # Component 3 shapes
    "comp3_width_in": (0.3, 0.8),
    "comp3_width_out": (0.2, 0.5),
    "comp3_length": (15.0, 25.0),
    "comp3_bend_height": (0.3, 0.8),

    # Component 3 POSITIONS - allow ±2μm adjustment from baseline
    "comp3_x_offset": (14.0, 18.0),  # Roughly where comp3 should be
    "comp3_y_offset": (-0.8, -0.2),  # Typically below center
}

# Baseline - initial guess including positions
BASELINE = {
    # Component 1
    "comp1_width_in": 0.5,
    "comp1_width_out": 0.3,
    "comp1_length": 20.0,
    "comp1_bend_height": 0.5,

    # Component 2
    "comp2_width_in": 0.35,
    "comp2_width_out": 0.15,
    "comp2_length": 8.0,
    "comp2_x_offset": 8.0,     # Initial position guess
    "comp2_y_offset": 0.0,     # Initially centered

    # Component 3
    "comp3_width_in": 0.5,
    "comp3_width_out": 0.3,
    "comp3_length": 20.0,
    "comp3_bend_height": 0.5,
    "comp3_x_offset": 16.0,    # Initial position guess
    "comp3_y_offset": -0.5,    # Initially slightly below
}


def main():
    """Run optimization with position parameters."""

    print("=" * 70)
    print("MULTI-COMPONENT OPTIMIZATION WITH POSITION PARAMETERS")
    print("=" * 70)
    print()
    print("This optimization includes BOTH shape AND position parameters.")
    print("Position params allow fine-tuning component placement to minimize SSE.")
    print()
    print(f"Total parameters: {len(PARAM_NAMES)}")
    print(f"  Shape parameters: {len(PARAM_NAMES) - 4}")
    print(f"  Position parameters: 4 (comp2_x/y, comp3_x/y)")
    print()

    # Check if required files exist
    target_image = SCRIPT_DIR / "target.png"
    calibration_file = SCRIPT_DIR / "calibration.json"

    if not target_image.exists():
        print(f"ERROR: Target image not found: {target_image}")
        print("Please create target.png and calibration.json first.")
        print()
        print("To create calibration:")
        print("  python -m core.calibrate_boundary \\")
        print("    --reference-image target.png \\")
        print("    --footprint-length-um 40.0 \\")
        print("    --footprint-width-um 2.0 \\")
        print("    --out calibration.json")
        return

    if not calibration_file.exists():
        print(f"ERROR: Calibration file not found: {calibration_file}")
        return

    # Configuration
    config = OptimizerConfig(
        target_image=target_image,
        calibration_file=calibration_file,
        output_dir=SCRIPT_DIR / "results_with_positions",
        layer=1,
        datatype=0,
        flip_y=True,
        footprint_penalty_enabled=True,
        footprint_penalty_weight=1.0,
        footprint_penalty_mode="match",
        method="Nelder-Mead",
        max_iterations=200,      # More iterations for larger param space
        max_function_evals=350,
        grid_um=GRID,
        verbose=True,
        print_every=5,
    )

    # Create optimizer
    optimizer = GDSOptimizer(
        factory_fn=make_device_with_positions,
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
    print("RESULTS WITH POSITION OPTIMIZATION")
    print("=" * 70)
    print(f"Baseline SSE: {result.baseline_sse:,.0f}")
    print(f"Best SSE: {result.best_sse:,.0f}")
    print(f"Improvement: {result.improvement_pct:.1f}%")
    print()

    if result.best_params:
        print("Position adjustments from baseline:")
        for key in ["comp2_x_offset", "comp2_y_offset", "comp3_x_offset", "comp3_y_offset"]:
            baseline_val = BASELINE[key]
            best_val = result.best_params[key]
            delta = best_val - baseline_val
            print(f"  {key}: {baseline_val:.3f} → {best_val:.3f} (Δ = {delta:+.3f} μm)")

    print()
    print("Position optimization allows the optimizer to fine-tune component")
    print("placement to minimize pixel differences, compensating for extraction")
    print("errors in the original calibration.")


if __name__ == "__main__":
    main()
