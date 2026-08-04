#!/usr/bin/env python3
"""
General-purpose GDS optimizer for the JEE framework.

This module provides a reusable optimizer class that works with any
parametric GDS factory function. It automatically enforces footprint
constraints via a penalty term.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
from PIL import Image
from scipy.optimize import minimize

try:
    import gdstk
except ImportError:
    gdstk = None

# Import from sibling modules
from . import gds_raster_compare as gds_cmp
from . import compare_fixed
from . import compute_sse as sse_mod
from .footprint_penalty import compute_footprint_penalty_from_polygons


@dataclass
class OptimizerConfig:
    """Configuration for GDS optimization."""

    # Required paths
    target_image: Path
    calibration_file: Path
    output_dir: Path

    # GDS layer/datatype
    layer: int = 1
    datatype: int = 0

    # Optimization settings
    method: str = "Nelder-Mead"
    max_iterations: int = 150
    max_function_evals: int = 250

    # Grid snapping (microns)
    grid_um: float = 0.002

    # Flip Y for image comparison (usually True for photonic layouts)
    flip_y: bool = True

    # Supersampling for rasterization
    supersample: int = 4

    # Footprint penalty settings
    footprint_penalty_enabled: bool = True
    footprint_penalty_weight: float = 1.0
    footprint_penalty_mode: str = "match"  # "exceed" or "match"

    # Verbosity
    verbose: bool = True
    print_every: int = 5


@dataclass
class OptimizationResult:
    """Result of an optimization run."""

    baseline_sse: float
    best_sse: float
    best_total_cost: float
    best_footprint_penalty: float
    best_params: Dict[str, float]
    iterations: int
    improvement_pct: float  # SSE improvement (geometric quality)
    within_footprint: bool
    total_cost_improvement_pct: float = 0.0  # SSE + penalty improvement
    history: List[Dict[str, Any]] = field(default_factory=list)


class GDSOptimizer:
    """
    General-purpose optimizer for parametric GDS designs.

    This optimizer works with ANY parametric GDS factory function and
    automatically enforces footprint constraints via a penalty term.

    Usage:
        optimizer = GDSOptimizer(
            factory_fn=my_component_factory,  # Callable[[Dict], gf.Component]
            param_names=['length', 'width', 'gap'],
            param_bounds={'length': (5, 20), 'width': (0.1, 0.5), 'gap': (0.01, 0.1)},
            baseline={'length': 10.0, 'width': 0.3, 'gap': 0.05},
            config=OptimizerConfig(
                target_image=Path("target.png"),
                calibration_file=Path("calibration.json"),
                output_dir=Path("results"),
            )
        )
        result = optimizer.run()
    """

    def __init__(
        self,
        factory_fn: Callable[[Dict[str, float]], Any],
        param_names: List[str],
        param_bounds: Dict[str, Tuple[float, float]],
        baseline: Dict[str, float],
        config: OptimizerConfig,
        int_params: Optional[set] = None,
    ):
        """
        Initialize the optimizer.

        Args:
            factory_fn: Function that takes params dict and returns gf.Component
            param_names: List of parameter names in optimization order
            param_bounds: Dict mapping param name to (min, max) bounds
            baseline: Dict of starting parameter values
            config: OptimizerConfig with paths and settings
            int_params: Optional set of parameter names that must be integers.
                        These are rounded after grid snapping to ensure integer values
                        are passed to scripts that declare them with `: int` type hints.
        """
        self.factory_fn = factory_fn
        self.param_names = param_names
        self.param_bounds = param_bounds
        self.baseline = baseline
        self.config = config
        self.int_params = int_params or set()

        # Load calibration
        with config.calibration_file.open() as f:
            self.calibration = json.load(f)

        # State tracking
        self._iteration = 0
        self._best_sse = float("inf")
        self._best_total_cost = float("inf")
        self._best_footprint_penalty = 0.0
        self._best_within_footprint = True
        self._best_params: Optional[Dict[str, float]] = None
        self._history: List[Dict[str, Any]] = []

        # Ensure output directory exists
        config.output_dir.mkdir(parents=True, exist_ok=True)
        self._work_dir = config.output_dir / "work"
        self._work_dir.mkdir(exist_ok=True)

    def _round_to_grid(self, val: float) -> float:
        """Snap value to grid."""
        return round(val / self.config.grid_um) * self.config.grid_um

    def _array_to_params(self, arr: np.ndarray) -> Dict[str, float]:
        """Convert optimization array to parameter dict.

        Applies bounds clipping, grid snapping, and integer rounding
        for parameters declared with `: int` type hints.
        """
        params = {}
        for i, name in enumerate(self.param_names):
            lo, hi = self.param_bounds[name]
            val = np.clip(arr[i], lo, hi)
            val = self._round_to_grid(val)
            # Round to integer if this parameter has an int type hint
            if name in self.int_params:
                val = float(int(round(val)))
            params[name] = val
        return params

    def _params_to_array(self, params: Dict[str, float]) -> np.ndarray:
        """Convert parameter dict to optimization array."""
        return np.array([params[name] for name in self.param_names])

    def _clean_gds(self, gds_path: Path) -> None:
        """Remove CONTEXT_INFO cells from GDS (gdsfactory artifact)."""
        if gdstk is None:
            return
        lib = gdstk.read_gds(str(gds_path))
        lib_clean = gdstk.Library()
        for cell in lib.cells:
            if "CONTEXT_INFO" not in cell.name:
                lib_clean.add(cell)
        lib_clean.write_gds(str(gds_path))

    def _evaluate(
        self, params: Dict[str, float]
    ) -> Tuple[float, float, float, bool, float, float]:
        """
        Evaluate a parameter set.

        Returns:
            (sse, footprint_penalty, total_cost, within_footprint, gds_length_um, gds_width_um)
        """
        try:
            # Generate component
            component = self.factory_fn(params)

            # Write GDS
            gds_path = self._work_dir / "component.gds"
            component.write_gds(str(gds_path))
            self._clean_gds(gds_path)

            # Extract polygons
            top = gds_cmp.load_top_cell(gds_path)
            polygons = gds_cmp.extract_polygons(
                top, self.config.layer, self.config.datatype
            )

            if not polygons:
                return float("inf"), 0.0, float("inf"), False, 0.0, 0.0

            # Get layout bbox
            lx0, ly0, lx1, ly1 = gds_cmp.polygons_bbox(polygons)

            # --- Compute footprint penalty ---
            footprint_penalty = 0.0
            within_footprint = True
            gds_length_um = lx1 - lx0
            gds_width_um = ly1 - ly0
            if self.config.footprint_penalty_enabled:
                fp_result = compute_footprint_penalty_from_polygons(
                    polygons=polygons,
                    target_footprint_um=tuple(self.calibration["footprint_um"]),
                    scale_px_per_um=tuple(self.calibration["scale_px_per_um"]),
                    mode=self.config.footprint_penalty_mode,
                )
                footprint_penalty = (
                    fp_result["penalty"] * self.config.footprint_penalty_weight
                )
                within_footprint = fp_result.get("within_bounds", True)
                # Use fp_result dimensions if available (more accurate)
                gds_length_um = fp_result.get("gds_length_um", gds_length_um)
                gds_width_um = fp_result.get("gds_width_um", gds_width_um)

            # --- Compute SSE via rasterization ---
            # Get image size from calibration
            W, H = self.calibration["image_size_px"]

            # Map polygons using fixed calibration
            mapped = compare_fixed.map_polygons_with_fixed_calibration(
                polygons=polygons,
                layout_bbox=(lx0, ly0, lx1, ly1),
                calibration=self.calibration,
                out_size=(W, H),
                flip_y=self.config.flip_y,
                supersample=self.config.supersample,
            )

            # Rasterize
            ss = self.config.supersample
            Wss, Hss = W * ss, H * ss
            raster_ss = gds_cmp.rasterize(mapped, (Wss, Hss))
            raster = raster_ss.resize((W, H), resample=Image.BOX)

            # Save raster for debugging
            raster_path = self._work_dir / "raster.png"
            raster.save(raster_path)

            # Compute SSE
            sse_result = sse_mod.compute_sse_metrics(
                self.config.target_image,
                raster_path,
                white_threshold=self.calibration.get("white_threshold", 245),
            )
            sse = sse_result["SSE"]

            # Total cost
            total_cost = sse + footprint_penalty

            return sse, footprint_penalty, total_cost, within_footprint, gds_length_um, gds_width_um

        except (FileNotFoundError, ValueError, OSError, KeyError, TypeError,
                AttributeError, RuntimeError, ImportError) as e:
            if self.config.verbose:
                print(f"    ERROR in _evaluate: {type(e).__name__}: {e}")
            return float("inf"), 0.0, float("inf"), False, 0.0, 0.0

    def _objective(self, arr: np.ndarray) -> float:
        """Objective function for scipy.optimize."""
        self._iteration += 1

        params = self._array_to_params(arr)
        sse, footprint_penalty, total_cost, within_footprint, gds_length_um, gds_width_um = self._evaluate(params)

        # Track best
        is_new_best = total_cost < self._best_total_cost
        if is_new_best:
            self._best_sse = sse
            self._best_total_cost = total_cost
            self._best_footprint_penalty = footprint_penalty
            self._best_within_footprint = within_footprint
            self._best_params = params.copy()

            # Save best params incrementally
            self._save_best_params()

        # Record history with params and GDS dimensions for visualization
        self._history.append(
            {
                "iteration": self._iteration,
                "sse": sse,
                "footprint_penalty": footprint_penalty,
                "total_cost": total_cost,
                "within_footprint": within_footprint,
                "is_best": is_new_best,
                "params": params.copy(),
                "gds_length_um": gds_length_um,
                "gds_width_um": gds_width_um,
            }
        )

        # Print progress
        if self.config.verbose:
            if self._iteration % self.config.print_every == 0 or is_new_best:
                marker = " *** NEW BEST ***" if is_new_best else ""
                fp_str = ""
                if self.config.footprint_penalty_enabled:
                    fp_str = f" + FP:{footprint_penalty:,.0f}"
                    if not within_footprint:
                        fp_str += " [EXCEEDS]"
                print(
                    f"[{self._iteration:4d}] SSE: {sse:,.0f}{fp_str} = {total_cost:,.0f} "
                    f"(best: {self._best_total_cost:,.0f}){marker}"
                )

        return total_cost

    def _save_best_params(self) -> None:
        """Save current best parameters to file."""
        if self._best_params is None:
            return

        result_data = {
            "best_sse": self._best_sse,
            "best_footprint_penalty": self._best_footprint_penalty,
            "best_total_cost": self._best_total_cost,
            "within_footprint": self._best_within_footprint,
            "iterations": self._iteration,
            "best_params": self._best_params,
        }
        with open(self.config.output_dir / "best_params.json", "w") as f:
            json.dump(result_data, f, indent=2)

    def run(self) -> OptimizationResult:
        """Run the optimization."""

        if self.config.verbose:
            print("=" * 60)
            print("GDS OPTIMIZATION (JEE Framework)")
            print("=" * 60)
            print(f"Target: {self.config.target_image}")
            print(f"Calibration: {self.config.calibration_file}")
            print(f"Output: {self.config.output_dir}")
            print()
            print(
                f"Footprint penalty: "
                f"{'ENABLED' if self.config.footprint_penalty_enabled else 'disabled'}"
            )
            if self.config.footprint_penalty_enabled:
                print(f"  Mode: {self.config.footprint_penalty_mode}")
                print(f"  Weight: {self.config.footprint_penalty_weight}")
                print(f"  Target: {self.calibration['footprint_um']} um")
            print()
            print(f"Parameters ({len(self.param_names)}):")
            for name in self.param_names:
                lo, hi = self.param_bounds[name]
                val = self.baseline[name]
                print(f"  {name}: {val} (bounds: {lo} - {hi})")
            print()

        # Evaluate baseline
        x0 = self._params_to_array(self.baseline)
        baseline_cost = self._objective(x0)
        baseline_sse = self._best_sse

        if self.config.verbose:
            print(f"\nBaseline: SSE={baseline_sse:,.0f}, Total={baseline_cost:,.0f}")
            print()
            print("=" * 60)
            print(f"Running {self.config.method} optimization...")
            print(f"Max iterations: {self.config.max_iterations}")
            print("=" * 60)
            print()

        # Run optimization
        minimize(
            self._objective,
            x0,
            method=self.config.method,
            options={
                "maxiter": self.config.max_iterations,
                "maxfev": self.config.max_function_evals,
                "disp": False,
                "adaptive": True,
            },
        )

        # SSE improvement (what users care about - geometric quality)
        improvement_pct = (
            ((baseline_sse - self._best_sse) / baseline_sse * 100)
            if baseline_sse > 0
            else 0
        )

        # Total cost improvement (SSE + footprint penalty combined)
        total_cost_improvement_pct = (
            ((baseline_cost - self._best_total_cost) / baseline_cost * 100)
            if baseline_cost > 0
            else 0
        )

        if self.config.verbose:
            print()
            print("=" * 60)
            print("OPTIMIZATION COMPLETE")
            print("=" * 60)
            print(f"Iterations: {self._iteration}")
            print(f"Baseline SSE: {baseline_sse:,.0f}")
            print(f"Best SSE: {self._best_sse:,.0f}")
            print(f"SSE improvement: {improvement_pct:.1f}%")
            if self.config.footprint_penalty_enabled:
                print(f"Best footprint penalty: {self._best_footprint_penalty:,.0f}")
                print(
                    f"Within footprint: "
                    f"{'YES' if self._best_within_footprint else 'NO'}"
                )
            print(f"Best total cost: {self._best_total_cost:,.0f}")
            print(f"Total cost improvement: {total_cost_improvement_pct:.1f}%")

        # Save final results
        if self._best_params:
            result_data = {
                "baseline_sse": baseline_sse,
                "best_sse": self._best_sse,
                "best_footprint_penalty": self._best_footprint_penalty,
                "best_total_cost": self._best_total_cost,
                "improvement_pct": improvement_pct,
                "total_cost_improvement_pct": total_cost_improvement_pct,
                "iterations": self._iteration,
                "within_footprint": self._best_within_footprint,
                "baseline_params": self.baseline,
                "best_params": self._best_params,
                "config": {
                    "footprint_penalty_enabled": self.config.footprint_penalty_enabled,
                    "footprint_penalty_weight": self.config.footprint_penalty_weight,
                    "method": self.config.method,
                    "max_iterations": self.config.max_iterations,
                },
            }
            with open(self.config.output_dir / "optimization_result.json", "w") as f:
                json.dump(result_data, f, indent=2)

            # Save iteration history for visualization
            history_data = {
                "metadata": {
                    "param_names": self.param_names,
                    "param_bounds": {k: list(v) for k, v in self.param_bounds.items()},
                    "target_footprint_um": self.calibration.get("footprint_um", []),
                    "total_iterations": self._iteration,
                    "method": self.config.method,
                    "baseline_params": self.baseline,
                },
                "history": self._history,
            }
            with open(self.config.output_dir / "iteration_history.json", "w") as f:
                json.dump(history_data, f, indent=2)

            # Save best GDS
            best_component = self.factory_fn(self._best_params)
            best_gds = self.config.output_dir / "best_component.gds"
            best_component.write_gds(str(best_gds))
            self._clean_gds(best_gds)

            if self.config.verbose:
                print()
                print("Best parameters:")
                for k, v in self._best_params.items():
                    print(f"  {k}: {v}")
                print()
                print(f"Results saved to: {self.config.output_dir}")

        return OptimizationResult(
            baseline_sse=baseline_sse,
            best_sse=self._best_sse,
            best_total_cost=self._best_total_cost,
            best_footprint_penalty=self._best_footprint_penalty,
            best_params=self._best_params or {},
            iterations=self._iteration,
            improvement_pct=improvement_pct,
            within_footprint=self._best_within_footprint,
            total_cost_improvement_pct=total_cost_improvement_pct,
            history=self._history,
        )
