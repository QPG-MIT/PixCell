#!/usr/bin/env python3
"""
Trident Optimizer using the EXACT original evaluation pipeline.
Uses compare_fixed.py and compute_sse.py for consistent SSE calculation.

Starting from starting_point (SSE 89,854)

JEE Framework - Paths configured for jee/examples/trident_mode_converter/
"""

import json
import subprocess
import sys
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
import gdsfactory as gf

# Paths - relative to this script location
SCRIPT_DIR = Path(__file__).parent.resolve()
JEE_ROOT = SCRIPT_DIR.parent.parent  # jee/examples/trident_mode_converter → jee

TARGET_PNG = SCRIPT_DIR / "target.png"
CALIBRATION = SCRIPT_DIR / "calibration.json"
SCRIPTS_DIR = JEE_ROOT / "core"  # jee/core/
PYTHON = sys.executable  # Use current Python interpreter
OUTPUT_DIR = SCRIPT_DIR / "results"

GRID = 0.002

# ACTUAL BEST baseline from starting_point (SSE 89,854)
BASELINE = {
    'mid_length': 16.0,
    'mid_width_in': 0.222,
    'mid_width_out': 0.102,
    'outer_length': 24.8,
    'outer_width_in': 0.102,
    'outer_width_out': 0.142,
    'gap_start': 0.050,
    'bend_length': 15.2,
    'bend_height': 0.506,
    'bend_width_end': 0.264,
}

PARAM_NAMES = list(BASELINE.keys())
PARAM_BOUNDS = {
    'mid_length': (10.0, 22.0),
    'mid_width_in': (0.15, 0.30),
    'mid_width_out': (0.06, 0.15),
    'outer_length': (22.0, 28.0),
    'outer_width_in': (0.06, 0.15),
    'outer_width_out': (0.10, 0.20),
    'gap_start': (0.03, 0.10),
    'bend_length': (12.0, 18.0),
    'bend_height': (0.35, 0.65),
    'bend_width_end': (0.18, 0.35),
}

def round_to_grid(val):
    return round(val / GRID) * GRID


@gf.cell
def tapered_s_bend(length=10.0, height=2.0, width_in=0.5, width_out=0.5, layer=(1, 0)):
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
    points = np.concatenate([
        np.stack([x_top, y_top], axis=1),
        np.stack([x_bot, y_bot], axis=1)[::-1]
    ])
    c.add_polygon(points, layer=layer)
    c.add_port(name="o1", center=(0, 0), width=width_in, orientation=180, layer=layer)
    c.add_port(name="o2", center=(length, height), width=width_out, orientation=0, layer=layer)
    return c


def array_to_params(arr):
    params = {}
    for i, name in enumerate(PARAM_NAMES):
        lo, hi = PARAM_BOUNDS[name]
        val = np.clip(arr[i], lo, hi)
        params[name] = round_to_grid(val)
    return params


def params_to_array(params):
    return np.array([params[name] for name in PARAM_NAMES])


def make_trident(params):
    c = gf.Component()
    layer = (1, 0)

    center = c << gf.components.taper(
        length=params['mid_length'],
        width1=params['mid_width_in'],
        width2=params['mid_width_out'],
        layer=layer
    )

    y_offset = (params['mid_width_in'] / 2) + params['gap_start'] + (params['outer_width_in'] / 2)

    top_s = c << gf.components.taper(
        length=params['outer_length'],
        width1=params['outer_width_in'],
        width2=params['outer_width_out'],
        layer=layer
    )
    top_s.movey(y_offset)

    top_b = c << tapered_s_bend(
        length=params['bend_length'],
        height=params['bend_height'],
        width_in=params['outer_width_out'],
        width_out=params['bend_width_end'],
        layer=layer
    )
    top_b.connect("o1", top_s.ports["o2"])

    bot_s = c << gf.components.taper(
        length=params['outer_length'],
        width1=params['outer_width_in'],
        width2=params['outer_width_out'],
        layer=layer
    )
    bot_s.movey(-y_offset)

    bot_b = c << tapered_s_bend(
        length=params['bend_length'],
        height=-params['bend_height'],
        width_in=params['outer_width_out'],
        width_out=params['bend_width_end'],
        layer=layer
    )
    bot_b.connect("o1", bot_s.ports["o2"])

    return c


def evaluate_with_original_pipeline(params, work_dir):
    """Evaluate using the exact original pipeline."""
    try:
        # Generate GDS
        component = make_trident(params)
        gds_path = work_dir / "test_component.gds"
        component.write_gds(str(gds_path))

        # Clean GDS (remove CONTEXT_INFO)
        import gdstk
        lib = gdstk.read_gds(str(gds_path))
        lib_clean = gdstk.Library()
        for cell in lib.cells:
            if "CONTEXT_INFO" not in cell.name:
                lib_clean.add(cell)
        lib_clean.write_gds(str(gds_path))

        # Run compare_fixed.py
        raster_path = work_dir / "raster.png"
        cmd_compare = [
            PYTHON, str(SCRIPTS_DIR / "compare_fixed.py"),
            "--gds", str(gds_path),
            "--layer", "1", "--datatype", "0",
            "--calibration", str(CALIBRATION),
            "--like", str(TARGET_PNG),
            "--flip-y",
            "--out", str(raster_path),
            "--compare-to", str(TARGET_PNG),
            "--diff", str(work_dir / "diff.png"),
            "--overlay", str(work_dir / "overlay.png"),
            "--report", str(work_dir / "metrics.json"),
        ]
        subprocess.run(cmd_compare, capture_output=True, cwd=str(SCRIPTS_DIR))

        # Run compute_sse.py
        sse_path = work_dir / "sse.json"
        cmd_sse = [
            PYTHON, str(SCRIPTS_DIR / "compute_sse.py"),
            "--raster", str(raster_path),
            "--target", str(TARGET_PNG),
            "--out", str(sse_path),
        ]
        subprocess.run(cmd_sse, capture_output=True, cwd=str(SCRIPTS_DIR))

        # Read SSE
        if sse_path.exists():
            result = json.loads(sse_path.read_text())
            return result.get("SSE", float('inf'))

        return float('inf')
    except Exception as e:
        print(f"    ERROR: {e}")
        return float('inf')


ITERATION = 0
BEST_SSE = float('inf')
BEST_PARAMS = None
WORK_DIR = None


def objective(arr):
    global ITERATION, BEST_SSE, BEST_PARAMS, WORK_DIR
    ITERATION += 1

    params = array_to_params(arr)
    sse = evaluate_with_original_pipeline(params, WORK_DIR)

    if sse < BEST_SSE:
        BEST_SSE = sse
        BEST_PARAMS = params.copy()
        marker = " *** NEW BEST ***"
    else:
        marker = ""

    if ITERATION % 5 == 0 or sse < BEST_SSE + 1:
        print(f"[{ITERATION:4d}] SSE: {sse:,.0f} (best: {BEST_SSE:,.0f}){marker}")

    return sse


def main():
    global BEST_SSE, BEST_PARAMS, WORK_DIR

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    WORK_DIR = OUTPUT_DIR / "work"
    WORK_DIR.mkdir(exist_ok=True)

    print("=" * 60)
    print("TRIDENT OPTIMIZATION (Original Pipeline)")
    print("=" * 60)
    print(f"Target: {TARGET_PNG}")
    print(f"Calibration: {CALIBRATION}")
    print()
    print("Baseline (starting_point, SSE 89,854):")
    for k, v in BASELINE.items():
        print(f"  {k}: {v}")
    print()

    x0 = params_to_array(BASELINE)

    print("Evaluating baseline with original pipeline...")
    baseline_sse = objective(x0)
    print(f"Baseline SSE: {baseline_sse:,.0f}")
    print()

    if baseline_sse > 100000:
        print("WARNING: Baseline SSE differs from expected 89,854")
        print("Check calibration and pipeline consistency")

    print("=" * 60)
    print("Running Nelder-Mead optimization (max 150 iterations)...")
    print("=" * 60)

    result = minimize(
        objective,
        x0,
        method='Nelder-Mead',
        options={
            'maxiter': 150,
            'maxfev': 250,
            'disp': True,
            'adaptive': True,
        }
    )

    print()
    print("=" * 60)
    print("OPTIMIZATION COMPLETE")
    print("=" * 60)
    print(f"Best SSE:  {BEST_SSE:,.0f}")
    print(f"Iterations: {ITERATION}")
    print()

    if BEST_PARAMS:
        print("Best parameters found:")
        for k, v in BEST_PARAMS.items():
            print(f"  {k}: {v}")

        improvement = baseline_sse - BEST_SSE
        pct_improvement = (improvement / baseline_sse) * 100 if baseline_sse > 0 else 0
        print(f"\nImprovement: {improvement:,.0f} ({pct_improvement:.1f}%)")

        with open(OUTPUT_DIR / "best_params.json", "w") as f:
            json.dump({
                "baseline_sse": baseline_sse,
                "best_sse": BEST_SSE,
                "improvement": improvement,
                "baseline_params": BASELINE,
                "best_params": BEST_PARAMS,
                "iterations": ITERATION
            }, f, indent=2)

        # Save final GDS
        best_component = make_trident(BEST_PARAMS)
        gds_path = OUTPUT_DIR / "best_trident.gds"
        best_component.write_gds(str(gds_path))
        print(f"\nBest GDS saved to: {gds_path}")


if __name__ == "__main__":
    main()
