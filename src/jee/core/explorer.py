#!/usr/bin/env python3
"""
GDS Explorer - Grid search + parallel multi-method optimization.

Combines coarse grid exploration with fine-grained local optimization
using Powell, Nelder-Mead, and CMA-ES methods in parallel.
"""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from itertools import product
from pathlib import Path
from threading import Lock
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

# CMA-ES is optional
try:
    import cma
    CMA_AVAILABLE = True
except ImportError:
    CMA_AVAILABLE = False

from .optimizer import GDSOptimizer, OptimizerConfig, OptimizationResult


@dataclass
class GridPoint:
    """A single point in the parameter grid."""
    params: Dict[str, float]
    sse: float
    footprint_penalty: float
    total_cost: float
    within_footprint: bool
    rank: int = 0


@dataclass
class LocalOptResult:
    """Result from a single local optimization run."""
    method: str
    starting_point_rank: int
    starting_params: Dict[str, float]
    starting_cost: float
    best_sse: float
    best_total_cost: float
    best_footprint_penalty: float
    best_params: Dict[str, float]
    iterations: int
    within_footprint: bool
    improvement_from_start: float  # percentage


@dataclass
class ExplorationResult:
    """Complete result from grid search + parallel optimization."""
    # Grid search results
    grid_points_evaluated: int
    grid_best_sse: float
    grid_best_cost: float
    grid_top_n: List[GridPoint]

    # Parallel optimization results
    local_opt_results: List[LocalOptResult]

    # Overall best
    best_sse: float
    best_total_cost: float
    best_footprint_penalty: float
    best_params: Dict[str, float]
    best_method: str
    best_starting_rank: int
    within_footprint: bool

    # Comparison
    baseline_sse: float
    improvement_from_baseline: float  # percentage
    improvement_from_grid: float  # percentage


@dataclass
class ExplorerConfig:
    """Configuration for GDSExplorer."""
    # Required paths
    target_image: Path = None
    calibration_file: Path = None
    output_dir: Path = None

    # Grid search settings
    grid_points_per_param: int = 5

    # Parallel optimization settings
    top_n_for_optimization: int = 3
    methods: List[str] = field(default_factory=lambda: ["Powell", "Nelder-Mead", "CMA-ES"])
    max_iterations_per_method: int = 100
    max_function_evals_per_method: int = 500
    parallel_workers: int = 4

    # CMA-ES specific settings
    cma_sigma0: float = 0.3  # Initial step size (fraction of parameter range)
    cma_popsize: Optional[int] = None  # Population size (None = auto)

    # Inherited from OptimizerConfig
    layer: int = 1
    datatype: int = 0
    flip_y: bool = True
    supersample: int = 4
    footprint_penalty_enabled: bool = True
    footprint_penalty_weight: float = 1.0
    footprint_penalty_mode: str = "match"
    grid_um: float = 0.002
    verbose: bool = True


class GDSExplorer:
    """
    Two-phase optimization: grid search followed by parallel local optimization.

    Phase 1: Grid search over parameter space to find promising regions
    Phase 2: Run multiple optimization methods in parallel from top N grid points

    Usage:
        explorer = GDSExplorer(
            factory_fn=make_component,
            param_names=['length', 'width'],
            param_bounds={'length': (5, 20), 'width': (0.1, 0.5)},
            baseline={'length': 10.0, 'width': 0.3},
            config=ExplorerConfig(
                target_image=Path("target.png"),
                calibration_file=Path("calibration.json"),
                output_dir=Path("results"),
            )
        )
        result = explorer.run()
    """

    def __init__(
        self,
        factory_fn: Callable[[Dict[str, float]], Any],
        param_names: List[str],
        param_bounds: Dict[str, Tuple[float, float]],
        baseline: Dict[str, float],
        config: ExplorerConfig,
        int_params: Optional[set] = None,
    ):
        self.factory_fn = factory_fn
        self.param_names = param_names
        self.param_bounds = param_bounds
        self.baseline = baseline
        self.config = config
        self.int_params = int_params or set()

        # Ensure paths are Path objects
        if config.target_image:
            config.target_image = Path(config.target_image)
        if config.calibration_file:
            config.calibration_file = Path(config.calibration_file)
        if config.output_dir:
            config.output_dir = Path(config.output_dir)

        # Thread-safe evaluation lock
        self._eval_lock = Lock()
        self._evaluator: Optional[GDSOptimizer] = None

    def _get_evaluator(self) -> GDSOptimizer:
        """Get or create evaluator for SSE computations."""
        if self._evaluator is None:
            opt_config = OptimizerConfig(
                target_image=self.config.target_image,
                calibration_file=self.config.calibration_file,
                output_dir=self.config.output_dir / "_eval_work",
                layer=self.config.layer,
                datatype=self.config.datatype,
                flip_y=self.config.flip_y,
                supersample=self.config.supersample,
                footprint_penalty_enabled=self.config.footprint_penalty_enabled,
                footprint_penalty_weight=self.config.footprint_penalty_weight,
                footprint_penalty_mode=self.config.footprint_penalty_mode,
                grid_um=self.config.grid_um,
                method="Nelder-Mead",
                max_iterations=1,
                verbose=False,
            )
            self._evaluator = GDSOptimizer(
                factory_fn=self.factory_fn,
                param_names=self.param_names,
                param_bounds=self.param_bounds,
                baseline=self.baseline,
                config=opt_config,
                int_params=self.int_params,
            )
        return self._evaluator

    def _evaluate(self, params: Dict[str, float]) -> Tuple[float, float, float, bool]:
        """Thread-safe parameter evaluation. Returns (sse, fp_penalty, total_cost, within_fp)."""
        with self._eval_lock:
            evaluator = self._get_evaluator()
            # _evaluate now returns 6 values, we only need the first 4 for grid search
            result = evaluator._evaluate(params)
            return result[:4]  # (sse, footprint_penalty, total_cost, within_footprint)

    def _round_to_grid(self, val: float) -> float:
        """Snap value to grid."""
        return round(val / self.config.grid_um) * self.config.grid_um

    def _snap_param(self, name: str, val: float) -> float:
        """Snap value to grid, then to integer if this param has an int type hint."""
        val = self._round_to_grid(val)
        if name in self.int_params:
            val = float(int(round(val)))
        return val

    def _generate_grid_values(
        self,
        param_values: Optional[Dict[str, List[float]]] = None
    ) -> List[Dict[str, float]]:
        """Generate all grid points from parameter values."""
        if param_values is None:
            # Auto-generate from bounds
            param_values = {}
            for name in self.param_names:
                lo, hi = self.param_bounds[name]
                n = self.config.grid_points_per_param
                # For integer params, generate integer grid values
                if name in self.int_params:
                    lo_int, hi_int = int(np.ceil(lo)), int(np.floor(hi))
                    # Use at most n integer values in range
                    int_range = list(range(lo_int, hi_int + 1))
                    if len(int_range) > n:
                        indices = np.linspace(0, len(int_range) - 1, n, dtype=int)
                        param_values[name] = [float(int_range[i]) for i in indices]
                    else:
                        param_values[name] = [float(v) for v in int_range]
                else:
                    param_values[name] = np.linspace(lo, hi, n).tolist()

        # Generate Cartesian product
        keys = list(param_values.keys())
        value_lists = [param_values[k] for k in keys]

        grid_points = []
        for combo in product(*value_lists):
            params = dict(zip(keys, combo))
            # Fill in any missing params from baseline
            for name in self.param_names:
                if name not in params:
                    params[name] = self.baseline.get(name, 0.0)
            # Round to grid and snap int params
            for name in params:
                params[name] = self._snap_param(name, params[name])
            grid_points.append(params)

        return grid_points

    def run_grid_search(
        self,
        param_values: Optional[Dict[str, List[float]]] = None,
        progress_callback: Optional[Callable] = None
    ) -> List[GridPoint]:
        """
        Run grid search over parameter space.

        Args:
            param_values: Optional dict mapping param name to list of values.
                         If None, auto-generates from bounds.
            progress_callback: Optional callback(current, total, best_cost)

        Returns:
            List of GridPoint sorted by total_cost (best first)
        """
        grid_points = self._generate_grid_values(param_values)
        total = len(grid_points)

        if self.config.verbose:
            print("=" * 60)
            print("GRID SEARCH PHASE")
            print("=" * 60)
            print(f"Total grid points: {total}")
            print()

        results = []
        best_cost = float("inf")

        for i, params in enumerate(grid_points):
            try:
                sse, fp_penalty, total_cost, within_fp = self._evaluate(params)
            except Exception as e:
                if self.config.verbose:
                    print(f"  Grid point {i+1} failed: {e}")
                sse = float("inf")
                fp_penalty = 0.0
                total_cost = float("inf")
                within_fp = False

            if total_cost < best_cost:
                best_cost = total_cost

            results.append(GridPoint(
                params=params.copy(),
                sse=sse,
                footprint_penalty=fp_penalty,
                total_cost=total_cost,
                within_footprint=within_fp,
            ))

            if progress_callback:
                progress_callback(i + 1, total, best_cost)

            if self.config.verbose and (i + 1) % 10 == 0:
                print(f"  [{i + 1}/{total}] Best so far: {best_cost:,.0f}")

        # Sort by total_cost and assign ranks
        results.sort(key=lambda x: x.total_cost)
        for rank, point in enumerate(results):
            point.rank = rank + 1

        if self.config.verbose:
            print()
            print(f"Grid search complete. Best cost: {results[0].total_cost:,.0f}")
            print(f"Top 3 points:")
            for i, pt in enumerate(results[:3]):
                print(f"  {i+1}. SSE={pt.sse:,.0f}, cost={pt.total_cost:,.0f}")

        return results

    def _run_cmaes_optimization(
        self,
        starting_point: GridPoint,
    ) -> LocalOptResult:
        """Run CMA-ES optimization from a starting point."""
        if not CMA_AVAILABLE:
            raise ImportError("cma package not installed. Install with: pip install cma")

        # Create output directory for this run
        run_output_dir = self.config.output_dir / f"opt_cma-es_rank{starting_point.rank}"
        run_output_dir.mkdir(parents=True, exist_ok=True)

        # Convert starting params to array
        x0 = [starting_point.params[name] for name in self.param_names]

        # Compute sigma0 - scale by parameter range
        sigma0_values = []
        for name in self.param_names:
            lo, hi = self.param_bounds[name]
            sigma0_values.append((hi - lo) * self.config.cma_sigma0)
        # Use average sigma0
        sigma0 = sum(sigma0_values) / len(sigma0_values)

        # Set bounds for CMA-ES
        bounds = [
            [self.param_bounds[name][0] for name in self.param_names],
            [self.param_bounds[name][1] for name in self.param_names],
        ]

        # CMA-ES options
        opts = {
            'bounds': bounds,
            'maxiter': self.config.max_iterations_per_method,
            'maxfevals': self.config.max_function_evals_per_method,
            'verbose': -9,  # Suppress output
            'verb_disp': 0,
            'verb_log': 0,
            'verb_time': False,
        }
        if self.config.cma_popsize:
            opts['popsize'] = self.config.cma_popsize

        # Track best result during optimization
        best_sse = float("inf")
        best_fp_penalty = 0.0
        best_cost = float("inf")
        best_within_fp = False
        best_params = starting_point.params.copy()
        iteration_count = 0

        # Create objective that uses our evaluation
        def objective(x):
            nonlocal best_sse, best_fp_penalty, best_cost, best_within_fp, best_params, iteration_count
            params = dict(zip(self.param_names, x))
            # Round to grid and snap int params
            for name in params:
                params[name] = self._snap_param(name, params[name])
            sse, fp_penalty, total_cost, within_fp = self._evaluate(params)
            iteration_count += 1

            # Track best
            if total_cost < best_cost:
                best_sse = sse
                best_fp_penalty = fp_penalty
                best_cost = total_cost
                best_within_fp = within_fp
                best_params = params.copy()

            return total_cost

        # Run CMA-ES
        es = cma.CMAEvolutionStrategy(x0, sigma0, opts)
        es.optimize(objective)

        # Round final best params (grid snap + int cast)
        for name in best_params:
            best_params[name] = self._snap_param(name, best_params[name])

        # Save results
        result_data = {
            "method": "CMA-ES",
            "starting_rank": starting_point.rank,
            "starting_cost": starting_point.total_cost,
            "best_sse": best_sse,
            "best_cost": best_cost,
            "best_params": best_params,
            "iterations": iteration_count,
        }
        with open(run_output_dir / "optimization_result.json", "w") as f:
            json.dump(result_data, f, indent=2)

        # Create work directory and save best GDS + raster (like Powell/Nelder-Mead)
        work_dir = run_output_dir / "work"
        work_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Save GDS
            best_component = self.factory_fn(best_params)
            best_gds = run_output_dir / "best_component.gds"
            best_component.write_gds(str(best_gds))

            # Also save to work dir
            work_gds = work_dir / "component.gds"
            best_component.write_gds(str(work_gds))

            # Generate and save raster using same approach as GDSOptimizer
            from . import gds_raster_compare as gds_cmp
            from . import compare_fixed
            from PIL import Image

            # Load calibration directly from file (same as optimizer does)
            with open(self.config.calibration_file) as f:
                calibration = json.load(f)

            top_cell = gds_cmp.load_top_cell(str(work_gds))
            polys = gds_cmp.extract_polygons(top_cell, layer=self.config.layer, datatype=self.config.datatype)

            if polys:
                lx0, ly0, lx1, ly1 = gds_cmp.polygons_bbox(polys)
                W, H = calibration["image_size_px"]
                ss = self.config.supersample

                mapped = compare_fixed.map_polygons_with_fixed_calibration(
                    polygons=polys,
                    layout_bbox=(lx0, ly0, lx1, ly1),
                    calibration=calibration,
                    out_size=(W, H),
                    flip_y=self.config.flip_y,
                    supersample=ss,
                )

                raster_ss = gds_cmp.rasterize(mapped, (W * ss, H * ss))
                raster = raster_ss.resize((W, H), resample=Image.BOX)
                raster.save(work_dir / "raster.png")
        except Exception as e:
            # Print error for debugging
            import traceback
            traceback.print_exc()

        improvement = 0.0
        if starting_point.total_cost > 0 and starting_point.total_cost < float("inf"):
            improvement = (starting_point.total_cost - best_cost) / starting_point.total_cost * 100

        return LocalOptResult(
            method="CMA-ES",
            starting_point_rank=starting_point.rank,
            starting_params=starting_point.params.copy(),
            starting_cost=starting_point.total_cost,
            best_sse=best_sse,
            best_total_cost=best_cost,
            best_footprint_penalty=best_fp_penalty,
            best_params=best_params,
            iterations=iteration_count,
            within_footprint=best_within_fp,
            improvement_from_start=improvement,
        )

    def _run_single_optimization(
        self,
        starting_point: GridPoint,
        method: str,
    ) -> LocalOptResult:
        """Run a single local optimization from a starting point."""
        # Dispatch CMA-ES to its own method
        if method == "CMA-ES":
            return self._run_cmaes_optimization(starting_point)

        # Create output directory for this run
        run_output_dir = self.config.output_dir / f"opt_{method.lower()}_rank{starting_point.rank}"
        run_output_dir.mkdir(parents=True, exist_ok=True)

        # Create fresh optimizer for this run (for scipy methods)
        opt_config = OptimizerConfig(
            target_image=self.config.target_image,
            calibration_file=self.config.calibration_file,
            output_dir=run_output_dir,
            layer=self.config.layer,
            datatype=self.config.datatype,
            flip_y=self.config.flip_y,
            supersample=self.config.supersample,
            footprint_penalty_enabled=self.config.footprint_penalty_enabled,
            footprint_penalty_weight=self.config.footprint_penalty_weight,
            footprint_penalty_mode=self.config.footprint_penalty_mode,
            grid_um=self.config.grid_um,
            method=method,
            max_iterations=self.config.max_iterations_per_method,
            max_function_evals=self.config.max_function_evals_per_method,
            verbose=False,
        )

        optimizer = GDSOptimizer(
            factory_fn=self.factory_fn,
            param_names=self.param_names,
            param_bounds=self.param_bounds,
            baseline=starting_point.params,
            config=opt_config,
            int_params=self.int_params,
        )

        result = optimizer.run()

        improvement = 0.0
        if starting_point.total_cost > 0 and starting_point.total_cost < float("inf"):
            improvement = (starting_point.total_cost - result.best_total_cost) / starting_point.total_cost * 100

        return LocalOptResult(
            method=method,
            starting_point_rank=starting_point.rank,
            starting_params=starting_point.params.copy(),
            starting_cost=starting_point.total_cost,
            best_sse=result.best_sse,
            best_total_cost=result.best_total_cost,
            best_footprint_penalty=result.best_footprint_penalty,
            best_params=result.best_params,
            iterations=result.iterations,
            within_footprint=result.within_footprint,
            improvement_from_start=improvement,
        )

    def run_parallel_optimization(
        self,
        top_grid_points: List[GridPoint],
        progress_callback: Optional[Callable] = None
    ) -> List[LocalOptResult]:
        """
        Run Powell and Nelder-Mead in parallel from top grid points.

        Args:
            top_grid_points: List of top N GridPoints to optimize from
            progress_callback: Optional callback(completed, total, best_result)

        Returns:
            List of LocalOptResult for all optimization runs
        """
        # Build list of (starting_point, method) pairs
        jobs = []
        for point in top_grid_points:
            for method in self.config.methods:
                jobs.append((point, method))

        total_jobs = len(jobs)

        if self.config.verbose:
            print()
            print("=" * 60)
            print("PARALLEL OPTIMIZATION PHASE")
            print("=" * 60)
            print(f"Starting points: {len(top_grid_points)}")
            print(f"Methods: {self.config.methods}")
            print(f"Total optimization runs: {total_jobs}")
            print(f"Parallel workers: {self.config.parallel_workers}")
            print()

        results = []
        completed = 0
        best_result: Optional[LocalOptResult] = None

        with ThreadPoolExecutor(max_workers=self.config.parallel_workers) as executor:
            futures = {
                executor.submit(self._run_single_optimization, point, method): (point, method)
                for point, method in jobs
            }

            for future in as_completed(futures):
                point, method = futures[future]
                try:
                    result = future.result()
                    results.append(result)

                    if best_result is None or result.best_total_cost < best_result.best_total_cost:
                        best_result = result

                    completed += 1

                    if self.config.verbose:
                        print(f"  [{completed}/{total_jobs}] {method} from rank {point.rank}: "
                              f"cost {result.best_total_cost:,.0f} "
                              f"(improved {result.improvement_from_start:.1f}%)")

                    if progress_callback and best_result:
                        progress_callback(completed, total_jobs, best_result)

                except Exception as e:
                    completed += 1
                    if self.config.verbose:
                        print(f"  [{completed}/{total_jobs}] ERROR: {method} from rank {point.rank} failed: {e}")

        # Sort by best_total_cost
        results.sort(key=lambda x: x.best_total_cost)

        return results

    def run(
        self,
        param_values: Optional[Dict[str, List[float]]] = None,
        progress_callback: Optional[Callable] = None
    ) -> ExplorationResult:
        """
        Run complete exploration: grid search + parallel optimization.

        Args:
            param_values: Optional dict for grid values (auto-generated if None)
            progress_callback: Optional callback for progress updates

        Returns:
            ExplorationResult with complete results
        """
        # Ensure output directory exists
        self.config.output_dir.mkdir(parents=True, exist_ok=True)

        # Evaluate baseline first
        try:
            baseline_sse, _, baseline_cost, _ = self._evaluate(self.baseline)
        except Exception:
            baseline_sse = float("inf")
            baseline_cost = float("inf")

        if self.config.verbose:
            print("=" * 60)
            print("GDS EXPLORER")
            print("=" * 60)
            print(f"Target: {self.config.target_image}")
            print(f"Parameters: {len(self.param_names)}")
            print(f"Baseline SSE: {baseline_sse:,.0f}")
            print()

        # Phase 1: Grid Search
        grid_results = self.run_grid_search(param_values)
        # Store for visualization export
        self._grid_results = grid_results

        # Select top N for optimization
        top_n = grid_results[:self.config.top_n_for_optimization]

        # Phase 2: Parallel Optimization
        opt_results = self.run_parallel_optimization(top_n)

        # Find overall best
        if opt_results:
            best = opt_results[0]  # Already sorted
        else:
            # Fallback to grid best
            best_grid = grid_results[0]
            best = LocalOptResult(
                method="grid",
                starting_point_rank=1,
                starting_params=best_grid.params,
                starting_cost=best_grid.total_cost,
                best_sse=best_grid.sse,
                best_total_cost=best_grid.total_cost,
                best_footprint_penalty=best_grid.footprint_penalty,
                best_params=best_grid.params,
                iterations=0,
                within_footprint=best_grid.within_footprint,
                improvement_from_start=0.0,
            )

        # Calculate improvements
        improvement_from_baseline = 0.0
        if baseline_cost > 0 and baseline_cost < float("inf"):
            improvement_from_baseline = (baseline_cost - best.best_total_cost) / baseline_cost * 100

        improvement_from_grid = 0.0
        if grid_results and grid_results[0].total_cost > 0 and grid_results[0].total_cost < float("inf"):
            improvement_from_grid = (grid_results[0].total_cost - best.best_total_cost) / grid_results[0].total_cost * 100

        result = ExplorationResult(
            grid_points_evaluated=len(grid_results),
            grid_best_sse=grid_results[0].sse if grid_results else float("inf"),
            grid_best_cost=grid_results[0].total_cost if grid_results else float("inf"),
            grid_top_n=top_n,
            local_opt_results=opt_results,
            best_sse=best.best_sse,
            best_total_cost=best.best_total_cost,
            best_footprint_penalty=best.best_footprint_penalty,
            best_params=best.best_params,
            best_method=best.method,
            best_starting_rank=best.starting_point_rank,
            within_footprint=best.within_footprint,
            baseline_sse=baseline_sse,
            improvement_from_baseline=improvement_from_baseline,
            improvement_from_grid=improvement_from_grid,
        )

        # Save results
        self._save_results(result)

        if self.config.verbose:
            self._print_summary(result)

        return result

    def _save_results(self, result: ExplorationResult) -> None:
        """Save exploration results to JSON."""
        result_dict = {
            "grid_points_evaluated": result.grid_points_evaluated,
            "grid_best_sse": result.grid_best_sse,
            "grid_best_cost": result.grid_best_cost,
            "best_sse": result.best_sse,
            "best_total_cost": result.best_total_cost,
            "best_footprint_penalty": result.best_footprint_penalty,
            "best_params": result.best_params,
            "best_method": result.best_method,
            "best_starting_rank": result.best_starting_rank,
            "within_footprint": result.within_footprint,
            "baseline_sse": result.baseline_sse,
            "improvement_from_baseline": result.improvement_from_baseline,
            "improvement_from_grid": result.improvement_from_grid,
            "local_opt_results": [
                {
                    "method": r.method,
                    "starting_rank": r.starting_point_rank,
                    "starting_cost": r.starting_cost,
                    "best_sse": r.best_sse,
                    "best_cost": r.best_total_cost,
                    "best_params": r.best_params,
                    "improvement": r.improvement_from_start,
                }
                for r in result.local_opt_results
            ],
        }

        with open(self.config.output_dir / "exploration_result.json", "w") as f:
            json.dump(result_dict, f, indent=2)

        # Also save best params separately
        with open(self.config.output_dir / "best_params.json", "w") as f:
            json.dump({
                "best_sse": result.best_sse,
                "best_method": result.best_method,
                "best_params": result.best_params,
            }, f, indent=2)

        # Save best GDS
        if result.best_params:
            try:
                best_component = self.factory_fn(result.best_params)
                best_gds = self.config.output_dir / "best_component.gds"
                best_component.write_gds(str(best_gds))
            except Exception as e:
                if self.config.verbose:
                    print(f"Warning: Failed to save best GDS: {e}")

        # Save full grid results for visualization
        if hasattr(self, "_grid_results") and self._grid_results:
            grid_data = {
                "metadata": {
                    "param_names": self.param_names,
                    "param_bounds": {k: list(v) for k, v in self.param_bounds.items()},
                    "grid_points_per_param": self.config.grid_points_per_param,
                    "total_points": len(self._grid_results),
                },
                "grid_points": [
                    {
                        "params": gp.params,
                        "sse": gp.sse,
                        "footprint_penalty": gp.footprint_penalty,
                        "total_cost": gp.total_cost,
                        "within_footprint": gp.within_footprint,
                        "rank": gp.rank,
                    }
                    for gp in self._grid_results
                ],
            }
            with open(self.config.output_dir / "grid_results.json", "w") as f:
                json.dump(grid_data, f, indent=2)

    def _print_summary(self, result: ExplorationResult) -> None:
        """Print exploration summary."""
        print()
        print("=" * 60)
        print("EXPLORATION COMPLETE")
        print("=" * 60)
        print()
        print("Grid Search:")
        print(f"  Points evaluated: {result.grid_points_evaluated}")
        print(f"  Best grid SSE: {result.grid_best_sse:,.0f}")
        print()
        print("Parallel Optimization:")
        print(f"  Runs completed: {len(result.local_opt_results)}")
        print(f"  Best method: {result.best_method}")
        print(f"  Started from grid rank: {result.best_starting_rank}")
        print()
        print("Overall Best:")
        print(f"  SSE: {result.best_sse:,.0f}")
        print(f"  Total cost: {result.best_total_cost:,.0f}")
        print(f"  Within footprint: {'YES' if result.within_footprint else 'NO'}")
        print()
        print("Improvements:")
        print(f"  From baseline: {result.improvement_from_baseline:.1f}%")
        print(f"  From grid best: {result.improvement_from_grid:.1f}%")
        print()
        print("Best parameters:")
        for k, v in result.best_params.items():
            print(f"  {k}: {v:.4f}")
        print()
        print(f"Results saved to: {self.config.output_dir}")
