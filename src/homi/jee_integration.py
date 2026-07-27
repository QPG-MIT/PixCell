"""
JEE Integration Module for HOMI

Bridges HOMI workflow with JEE optimizer for GDS parameter fine-tuning.
JEE uses SSE (Sum of Squared Errors) as its cost function - the same metric
HOMI uses to rank GDS candidates, making this integration natural.
"""

import json
import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

try:
    import gdsfactory as gf
except ImportError:
    gf = None

# JEE's optimizer core, imported by its absolute package name. Historically both
# jee/core and Weber/core were also reachable as a top-level ``core`` via path
# insertion, which required module-table surgery here; the src/ package layout and
# absolute imports fixed the clash structurally (see tests/test_core_import_order.py).
from jee.core import (
    GDSOptimizer,
    OptimizerConfig,
    calculate_calibration,
)

# Import Weber for script analysis (already set up in weber_integration)
from homi import weber_integration


def prepare_calibration(
    target_image_path: Path,
    footprint_json_path: Path,
    output_path: Path
) -> Path:
    """
    Generate calibration.json from target image and footprint.

    The calibration maps between physical coordinates (microns) and
    pixel coordinates for SSE comparison.

    Args:
        target_image_path: Path to device_bw.png (the target)
        footprint_json_path: Path to component/footprint.json
        output_path: Where to save calibration.json

    Returns:
        Path to generated calibration.json
    """
    target_image_path = Path(target_image_path)
    footprint_json_path = Path(footprint_json_path)
    output_path = Path(output_path)

    # Load footprint
    with open(footprint_json_path) as f:
        footprint = json.load(f)

    # Extract dimensions - footprint_um is [length, width]
    footprint_um = footprint.get("footprint_um", [])
    if len(footprint_um) >= 2:
        length_um, width_um = footprint_um[0], footprint_um[1]
    else:
        # Fallback to individual fields
        length_um = footprint.get("length_um", 10.0)
        width_um = footprint.get("width_um", 5.0)

    # Calculate calibration using JEE's function
    cal = calculate_calibration(
        reference_image=target_image_path,
        footprint_length_um=length_um,
        footprint_width_um=width_um,
        white_threshold=245
    )

    # Save calibration
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(cal, f, indent=2)

    return output_path


def _detect_int_params(script_source: str, param_names: List[str]) -> set:
    """
    Detect which parameters have integer type hints in the script source.

    Scans for patterns like `name: int = 5` or `name : int = 5` to identify
    parameters that must remain integers during optimization.

    Args:
        script_source: The Python script source code
        param_names: List of parameter names to check

    Returns:
        Set of parameter names that have int type hints
    """
    int_params = set()
    for name in param_names:
        # Match: name : int = ... (with optional whitespace)
        pattern = rf'\b{re.escape(name)}\s*:\s*int\s*='
        if re.search(pattern, script_source):
            int_params.add(name)
    return int_params


def apply_parameter_values(
    script_source: str,
    values: Dict[str, float],
    *,
    int_params: Optional[set[str]] = None,
) -> str:
    """Return source with declared top-level numeric parameters updated.

    JEE's optimizer evaluates candidates from rewritten source, but its output
    used to stop at ``best_params.json``.  Promotion needs an auditable Python
    artifact whose named dimensions equal the optimized values.  Restrict the
    rewrite to column-zero assignments so a same-named local variable cannot
    be changed accidentally, preserve annotations/comments, and fail closed
    when a requested parameter is not part of the program contract.
    """
    rewritten = script_source
    integers = int_params or set()
    missing: list[str] = []
    for name, raw_value in values.items():
        value: float | int = float(raw_value)
        if name in integers:
            value = int(round(value))
        pattern = (
            rf"(?m)^(?P<prefix>{re.escape(name)}\s*"
            rf"(?::\s*[^=\n]+)?\s*=\s*)"
            rf"(?P<value>-?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)"
        )
        rewritten, count = re.subn(
            pattern,
            lambda match, replacement=repr(value): match.group("prefix") + replacement,
            rewritten,
            count=1,
        )
        if count != 1:
            missing.append(name)
    if missing:
        raise ValueError(
            "optimized parameters are not top-level numeric assignments: "
            + ", ".join(sorted(missing))
        )
    return rewritten


def extract_factory_and_params(
    script_path: Path
) -> Tuple[Callable, List[str], Dict[str, Tuple[float, float]], Dict[str, float], set]:
    """
    Extract parametric factory function and parameter info from Michaelangelo script.

    Uses Weber's analyzer to get parameter info, then creates bounds.

    Args:
        script_path: Path to the generated Python script (e.g., best.py)

    Returns:
        - factory_fn: Callable that takes params dict and returns gf.Component
        - param_names: List of parameter names in optimization order
        - param_bounds: Dict mapping param name to (min, max)
        - baseline: Dict of starting parameter values
        - int_params: Set of parameter names that must be integers
    """
    script_path = Path(script_path)
    script_source = script_path.read_text()

    # Use Weber's analyzer to get parameter info
    analysis, slot_config = weber_integration.analyze_and_configure(script_source)
    params = weber_integration.get_parameter_info_for_ui(slot_config)

    # Convert to JEE format
    param_names = []
    param_bounds = {}
    baseline = {}

    for p in params:
        name = p["name"]

        # Skip non-numeric or layer parameters
        if not isinstance(p.get("default_value"), (int, float)):
            continue
        if "layer" in name.lower():
            continue

        param_names.append(name)
        param_bounds[name] = (p["min_value"], p["max_value"])
        baseline[name] = float(p["default_value"])

    # Detect integer-typed parameters from script source
    int_params = _detect_int_params(script_source, param_names)

    # Get main function name
    main_function = analysis.main_function

    # Create factory function (with int-awareness)
    factory_fn = _create_parametric_factory(
        script_source, main_function, param_names, int_params, script_path=script_path
    )

    return factory_fn, param_names, param_bounds, baseline, int_params


def _create_parametric_factory(
    script_source: str,
    main_function: Optional[str],
    param_names: List[str],
    int_params: Optional[set] = None,
    script_path: Optional[Path] = None
) -> Callable:
    """
    Create a factory function from script source.

    The returned function takes a params dict and returns a gf.Component.
    This wraps the script execution to allow JEE to call it with different params.

    Uses regex substitution (like Weber) to modify variable assignments in the
    script source before execution, ensuring local variable assignments inside
    functions receive the optimized values.

    Integer-typed parameters (detected via `: int` type hints) are rounded
    before substitution to prevent TypeError when the script uses them in
    integer-only contexts like range(), indexing, etc.
    """
    int_params = int_params or set()

    def factory(params: Dict[str, float]) -> Any:
        # Clear GDSFactory cache for fresh component
        if gf:
            gf.clear_cache()

        # Modify script source using regex (like Weber does)
        # Replace variable assignments like "var_name = 0.5" with new values
        # This approach works for local variables inside functions, unlike namespace injection
        modified_source = script_source
        for name, value in params.items():
            # Cast to int if the script declares this parameter with `: int` type hint
            if name in int_params:
                value = int(round(value))

            # Pattern matches: variable_name = number OR variable_name: type = number
            # Handles type hints like `: float`, `: int`, `: tuple[int, int]`, etc.
            pattern = rf'(\b{re.escape(name)}\s*(?::\s*[^=]+)?\s*=\s*)(-?\d+\.?\d*)'
            replacement = rf'\g<1>{value}'
            modified_source = re.sub(pattern, replacement, modified_source)

        # Create namespace with gdsfactory and numpy
        namespace = {
            'gf': gf,
            'gdsfactory': gf,
            'np': np,
            'numpy': np,
            '__name__': '__jee_optimizer__',
        }
        # Scripts that locate their outputs via __file__ (e.g. writing
        # lengths.json beside their GDS) crash under exec without it.
        if script_path is not None:
            namespace['__file__'] = str(script_path)

        # Also inject into namespace (for scripts that may use globals)
        for name, value in params.items():
            # Respect int types in namespace injection too
            if name in int_params:
                namespace[name] = int(round(value))
            else:
                namespace[name] = value

        # Execute the modified script
        exec(modified_source, namespace)

        # Get the component - call WITHOUT params since values are baked into source
        if main_function and main_function in namespace:
            result = namespace[main_function]
            if callable(result):
                return result()
            return result

        # Fallback: look for @gf.cell decorated function
        for key, val in namespace.items():
            if callable(val) and hasattr(val, '_cell_name'):
                return val()

        # Fallback: look for Component instance
        for key, val in namespace.items():
            if gf and isinstance(val, gf.Component):
                return val

        raise RuntimeError("Could not build component from script")

    return factory


def run_jee_optimization(
    script_path: Path,
    target_image_path: Path,
    calibration_path: Path,
    output_dir: Path,
    config: Dict[str, Any],
    progress_callback: Optional[Callable] = None
) -> Dict[str, Any]:
    """
    Run JEE optimization on the best script.

    Args:
        script_path: Path to best.py
        target_image_path: Path to device_bw.png
        calibration_path: Path to calibration.json
        output_dir: Where to save optimization results
        config: Optimization settings dict with:
            - max_iterations: int (default 100)
            - max_function_evals: int (default 200)
            - method: str (default "Nelder-Mead")
            - footprint_penalty_enabled: bool (default True)
            - footprint_penalty_weight: float (default 1.0)
            - footprint_penalty_mode: str (default "match")
        progress_callback: Optional callback for UI updates
            Called with dict: {iteration, sse, best_sse, best_total_cost, footprint_penalty}

    Returns:
        Dict with optimization results:
            - baseline_sse: float
            - best_sse: float
            - best_total_cost: float
            - best_footprint_penalty: float
            - best_params: dict
            - iterations: int
            - improvement_pct: float
            - within_footprint: bool
            - history: list
            - error: str (only if failed)
    """
    script_path = Path(script_path)
    target_image_path = Path(target_image_path)
    calibration_path = Path(calibration_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Extract factory and parameters
    try:
        factory_fn, param_names, param_bounds, baseline, int_params = extract_factory_and_params(
            script_path
        )
    except Exception as e:
        return {
            "error": f"Failed to extract parameters: {e}",
            "improvement_pct": 0,
            "baseline_sse": 0,
            "best_sse": 0,
        }

    if not param_names:
        return {
            "error": "No tunable parameters found in script",
            "improvement_pct": 0,
            "baseline_sse": 0,
            "best_sse": 0,
        }

    # Create optimizer config
    opt_config = OptimizerConfig(
        target_image=target_image_path,
        calibration_file=calibration_path,
        output_dir=output_dir,
        layer=1,
        datatype=0,
        flip_y=True,
        footprint_penalty_enabled=config.get("footprint_penalty_enabled", True),
        footprint_penalty_weight=config.get("footprint_penalty_weight", 1.0),
        footprint_penalty_mode=config.get("footprint_penalty_mode", "match"),
        method=config.get("method", "Nelder-Mead"),
        max_iterations=config.get("max_iterations", 100),
        max_function_evals=config.get("max_function_evals", 200),
        verbose=True,
        print_every=5,
    )

    # Create optimizer - potentially with callback wrapper
    if progress_callback:
        optimizer = _CallbackOptimizer(
            factory_fn=factory_fn,
            param_names=param_names,
            param_bounds=param_bounds,
            baseline=baseline,
            config=opt_config,
            callback=progress_callback,
            int_params=int_params,
        )
    else:
        optimizer = GDSOptimizer(
            factory_fn=factory_fn,
            param_names=param_names,
            param_bounds=param_bounds,
            baseline=baseline,
            config=opt_config,
            int_params=int_params,
        )

    # Run optimization
    try:
        result = optimizer.run()
    except Exception as e:
        return {
            "error": f"Optimization failed: {e}",
            "improvement_pct": 0,
            "baseline_sse": 0,
            "best_sse": 0,
        }

    return {
        "baseline_sse": result.baseline_sse,
        "best_sse": result.best_sse,
        "best_total_cost": result.best_total_cost,
        "best_footprint_penalty": result.best_footprint_penalty,
        "best_params": result.best_params,
        "iterations": result.iterations,
        "improvement_pct": result.improvement_pct,
        "within_footprint": result.within_footprint,
        "history": result.history,
    }


class _CallbackOptimizer(GDSOptimizer):
    """GDSOptimizer subclass that calls a progress callback."""

    def __init__(
        self,
        factory_fn: Callable,
        param_names: List[str],
        param_bounds: Dict[str, Tuple[float, float]],
        baseline: Dict[str, float],
        config: OptimizerConfig,
        callback: Callable,
        int_params: Optional[set] = None,
    ):
        super().__init__(factory_fn, param_names, param_bounds, baseline, config, int_params=int_params)
        self._callback = callback

    def _objective(self, arr) -> float:
        result = super()._objective(arr)

        # Call progress callback
        if self._callback:
            self._callback({
                "iteration": self._iteration,
                "sse": self._history[-1]["sse"] if self._history else float("inf"),
                "best_sse": self._best_sse,
                "best_total_cost": self._best_total_cost,
                "footprint_penalty": self._best_footprint_penalty,
                "is_best": self._history[-1].get("is_best", False) if self._history else False,
            })

        return result


def convert_weber_params_to_jee_bounds(
    params: List[Dict[str, Any]]
) -> Tuple[List[str], Dict[str, Tuple[float, float]], Dict[str, float]]:
    """
    Convert Weber's parameter info format to JEE optimizer format.

    Weber format: [{"name": "x", "min_value": 0, "max_value": 10, "default_value": 5}, ...]
    JEE format: (["x"], {"x": (0, 10)}, {"x": 5})

    Args:
        params: List of parameter dicts from Weber's get_parameter_info_for_ui()

    Returns:
        Tuple of (param_names, param_bounds, baseline)
    """
    param_names = []
    param_bounds = {}
    baseline = {}

    for p in params:
        name = p["name"]

        # Skip non-numeric
        if not isinstance(p.get("default_value"), (int, float)):
            continue
        # Skip layer parameters
        if "layer" in name.lower():
            continue

        param_names.append(name)
        param_bounds[name] = (p["min_value"], p["max_value"])
        baseline[name] = float(p["default_value"])

    return param_names, param_bounds, baseline


def get_jee_default_config() -> Dict[str, Any]:
    """Get default JEE optimization configuration."""
    return {
        "max_iterations": 100,
        "max_function_evals": 200,
        "method": "Nelder-Mead",
        "footprint_penalty_enabled": True,
        "footprint_penalty_weight": 1.0,
        "footprint_penalty_mode": "match",
    }


def run_jee_exploration(
    script_path: Path,
    target_image_path: Path,
    calibration_path: Path,
    output_dir: Path,
    config: Optional[Dict[str, Any]] = None,
    progress_callback: Optional[Callable] = None
) -> Dict[str, Any]:
    """
    Run JEE exploration: grid search + parallel multi-method optimization.

    This is an enhanced optimization that:
    1. Runs grid search to find promising parameter regions
    2. Runs multiple optimization methods in parallel from top N grid points
    3. Returns the best result across all optimization runs

    Args:
        script_path: Path to the GDSFactory Python script
        target_image_path: Path to target device image (PNG)
        calibration_path: Path to calibration.json
        output_dir: Where to save exploration results
        config: Optional dict with exploration settings:
            - grid_points_per_param: int (default 5)
            - top_n_for_optimization: int (default 3)
            - methods: List[str] (default ["Powell", "Nelder-Mead"])
            - max_iterations_per_method: int (default 100)
            - parallel_workers: int (default 4)
            - footprint_penalty_enabled: bool (default True)
            - footprint_penalty_weight: float (default 1.0)
            - footprint_penalty_mode: str (default "match")
            - param_values: Optional dict for custom grid values
        progress_callback: Optional progress callback

    Returns:
        Dict with exploration results including best_sse, best_params, best_method
    """
    # Import explorer here to avoid circular imports
    from jee.core import GDSExplorer, ExplorerConfig

    script_path = Path(script_path)
    target_image_path = Path(target_image_path)
    calibration_path = Path(calibration_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Get config with defaults
    config = config or {}
    grid_points_per_param = config.get("grid_points_per_param", 5)
    top_n = config.get("top_n_for_optimization", 3)
    methods = config.get("methods", ["Powell", "Nelder-Mead"])
    max_iterations = config.get("max_iterations_per_method", 100)
    parallel_workers = config.get("parallel_workers", 4)
    param_values = config.get("param_values")
    footprint_enabled = config.get("footprint_penalty_enabled", True)
    footprint_weight = config.get("footprint_penalty_weight", 1.0)
    footprint_mode = config.get("footprint_penalty_mode", "match")

    # Extract factory and parameters
    try:
        factory_fn, param_names, param_bounds, baseline, int_params = extract_factory_and_params(
            script_path
        )
    except Exception as e:
        return {
            "error": f"Failed to extract parameters: {e}",
            "best_sse": 0,
            "improvement_from_baseline": 0,
        }

    if not param_names:
        return {
            "error": "No tunable parameters found in script",
            "best_sse": 0,
            "improvement_from_baseline": 0,
        }

    # Create explorer config
    explorer_config = ExplorerConfig(
        target_image=target_image_path,
        calibration_file=calibration_path,
        output_dir=output_dir,
        grid_points_per_param=grid_points_per_param,
        top_n_for_optimization=top_n,
        methods=methods,
        max_iterations_per_method=max_iterations,
        max_function_evals_per_method=max_iterations * 2,
        parallel_workers=parallel_workers,
        footprint_penalty_enabled=footprint_enabled,
        footprint_penalty_weight=footprint_weight,
        footprint_penalty_mode=footprint_mode,
        verbose=True,
    )

    # Create explorer
    explorer = GDSExplorer(
        factory_fn=factory_fn,
        param_names=param_names,
        param_bounds=param_bounds,
        baseline=baseline,
        config=explorer_config,
        int_params=int_params,
    )

    # Run exploration
    try:
        result = explorer.run(param_values=param_values, progress_callback=progress_callback)
    except Exception as e:
        return {
            "error": f"Exploration failed: {e}",
            "best_sse": 0,
            "improvement_from_baseline": 0,
        }

    return {
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
        "local_opt_count": len(result.local_opt_results),
        "all_results": [
            {
                "method": r.method,
                "starting_rank": r.starting_point_rank,
                "best_sse": r.best_sse,
                "best_cost": r.best_total_cost,
                "improvement": r.improvement_from_start,
            }
            for r in result.local_opt_results
        ],
    }


def visualize_exploration_results(
    results_dir: Path,
    output_dir: Optional[Path] = None,
    style: str = "dark"
) -> Dict[str, Any]:
    """
    Generate visualization figures for JEE exploration results.

    Creates matplotlib figures showing:
    - Grid search SSE distribution
    - Method comparison (Powell vs Nelder-Mead)
    - Improvement breakdown by run
    - Convergence curves from iteration histories
    - Parameter evolution during optimization
    - Summary figure

    Args:
        results_dir: Directory containing exploration_result.json and related files
        output_dir: Where to save figures (default: results_dir/figures)
        style: Plot style - "dark" or "light"

    Returns:
        Dict with:
            - status: "success" or "error"
            - figures: List of generated figure paths
            - output_dir: Path to figures directory
            - error: Error message if failed
    """
    # Import visualization module
    from jee.core.visualize_exploration import create_visualization_report

    results_dir = Path(results_dir)

    try:
        figure_paths = create_visualization_report(
            results_dir=results_dir,
            output_dir=output_dir,
            style=style,
        )
        return {
            "status": "success",
            "figures": [str(p) for p in figure_paths],
            "output_dir": str(output_dir or results_dir / "figures"),
            "count": len(figure_paths),
        }
    except FileNotFoundError as e:
        return {
            "status": "error",
            "error": f"Results not found: {e}",
            "figures": [],
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "figures": [],
        }
