"""
GDS Generation Module

Wrapper for Michaelangelo's GDS generation pipeline with progress callbacks.
Supports multiple AI providers via the unified model client:

- Google Gemini (direct API) - 5 models
- Anthropic Claude (direct API) - 9 models
- OpenAI GPT (direct API) - 10 models
- Meta Llama (via OpenRouter) - 4 models
- Moonshot Kimi (via OpenRouter) - 4 models
- Alibaba Qwen-VL (via OpenRouter) - 22 models

Total: 54 vision-language models for GDS generation.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Callable, List, Optional

# Load environment variables from .env (upward search / checkout / ~/.pixcell/env)
try:
    from homi.paths import load_env
    load_env()
except ImportError:
    pass  # dotenv not installed, assume env vars are set

# Import model client for model listing
try:
    from homi.model_client import list_models, list_providers, get_model_capabilities
except ImportError:
    # Fallback if model_client not yet installed
    def list_models(provider=None):
        return []
    def list_providers():
        return []
    def get_model_capabilities(model_name):
        return None

# Import exploration tree for structured callback parsing
try:
    from homi.exploration_tree import parse_exploration_log_line
except ImportError:
    # Fallback if exploration_tree not available
    def parse_exploration_log_line(line):
        return None

# Default prompts (from michaelangelo/templates/)
DEFAULT_PROMPT = """Study the device in the attached PNG. Recreate this geometry using GDSFactory parametric functions from the attached catalog.

IMPORTANT: Do NOT use raw polygon coordinates (add_polygon, from_polygon, or hardcoded vertex lists). Build the shape by composing parametric primitives and boolean operations.

The footprint of the device is attached. Analyze the image carefully, then write the required Python script."""

DEFAULT_ITERATION_PROMPT = """The attached image shows how your current code rasters. Think deeply about how we can change the script to move towards the original image I gave you."""


def setup_component_directory(
    component_dir: Path,
    device_bw_path: str,
    footprint_length_um: float,
    footprint_width_um: float,
    custom_prompt: Optional[str] = None,
    custom_iteration_prompt: Optional[str] = None
) -> Path:
    """
    Set up a component directory for Michaelangelo.

    Args:
        component_dir: Path to create/setup the component directory
        device_bw_path: Path to the B&W device image
        footprint_length_um: Device length in micrometers
        footprint_width_um: Device width in micrometers
        custom_prompt: Optional custom initial prompt
        custom_iteration_prompt: Optional custom iteration prompt

    Returns:
        Path to the component directory
    """
    component_dir = Path(component_dir)
    component_dir.mkdir(parents=True, exist_ok=True)

    # Copy device image as component.png
    component_png = component_dir / "component.png"
    shutil.copy2(device_bw_path, component_png)

    # Create footprint.json
    footprint = {"footprint_um": [footprint_length_um, footprint_width_um]}
    footprint_path = component_dir / "footprint.json"
    with open(footprint_path, "w") as f:
        json.dump(footprint, f, indent=2)

    # Create prompt.md
    prompt_path = component_dir / "prompt.md"
    with open(prompt_path, "w") as f:
        f.write(custom_prompt or DEFAULT_PROMPT)

    # Create iteration_prompt.md
    iteration_prompt_path = component_dir / "iteration_prompt.md"
    with open(iteration_prompt_path, "w") as f:
        f.write(custom_iteration_prompt or DEFAULT_ITERATION_PROMPT)

    return component_dir


def run_calibration(component_dir: Path, michaelangelo_dir: Path) -> bool:
    """
    Generate calibration.json for the component.

    Args:
        component_dir: Path to component directory
        michaelangelo_dir: Path to michaelangelo installation

    Returns:
        True if successful
    """
    calibrate_script = michaelangelo_dir / "core" / "calibrate_boundary.py"
    component_png = component_dir / "component.png"
    footprint_path = component_dir / "footprint.json"
    calibration_path = component_dir / "calibration.json"

    if calibration_path.exists():
        return True

    # Load footprint
    with open(footprint_path) as f:
        footprint = json.load(f)

    length_um = footprint["footprint_um"][0]
    width_um = footprint["footprint_um"][1]

    cmd = [
        sys.executable, str(calibrate_script),
        "--reference-image", str(component_png),
        "--footprint-length-um", str(length_um),
        "--footprint-width-um", str(width_um),
        "--out", str(calibration_path)
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return result.returncode == 0 and calibration_path.exists()
    except Exception as e:
        print(f"Calibration failed: {e}")
        return False


def _sanitize_model_name(model: str) -> str:
    """Sanitize model name for use in directory names."""
    # Extract model ID from unified format (provider/model-name)
    model_id = model.split("/")[-1] if "/" in model else model
    # Replace characters that could cause issues in paths
    return model_id.replace("/", "-").replace(".", "-")


def run_phase1(
    component_dir: Path,
    michaelangelo_dir: Path,
    base_seed: int = 1333,
    seed_range: int = 12,
    num_parallel: int = 8,
    model: str = "gemini/gemini-3-flash-preview",
    progress_callback: Optional[Callable[[dict], None]] = None,
    reasoning_effort: str = "high"
) -> dict:
    """
    Run Phase 1: Multi-turn seed exploration.

    Args:
        component_dir: Path to component directory
        michaelangelo_dir: Path to michaelangelo installation
        base_seed: Base seed for exploration
        seed_range: Range around base seed (+/-)
        num_parallel: Number of parallel workers
        model: Model to use (unified format: provider/model-name)
            Examples:
            - "gemini/gemini-3-flash-preview" (default)
            - "anthropic/claude-sonnet-4.5"
            - "openai/gpt-5.2"
            - "qwen/qwen3-vl-235b-a22b-thinking"
        progress_callback: Optional callback for progress updates
        reasoning_effort: Thinking/reasoning effort level (high, medium, low)

    Returns:
        Exploration summary dict
    """
    # Use new multi-model script if available, fallback to gemini-specific
    phase1_script = michaelangelo_dir / "core" / "multiturn_seed_exploration.py"
    if not phase1_script.exists():
        phase1_script = michaelangelo_dir / "core" / "gemini_multiturn_seed_exploration.py"

    # Model-specific output directory to prevent overwriting between models
    sanitized_model = _sanitize_model_name(model)
    output_dir = component_dir / "phase1" / f"benchmark_{sanitized_model}"

    # Use absolute paths to avoid nesting issues in subprocess
    component_dir_abs = Path(component_dir).resolve()
    output_dir_abs = Path(output_dir).resolve()

    cmd = [
        sys.executable, str(phase1_script),
        "--component-dir", str(component_dir_abs),
        "--output-dir", str(output_dir_abs),
        "--base-seed", str(base_seed),
        "--seed-range", str(seed_range),
        "--num-parallel", str(num_parallel),
        "--model", model,
        "--reasoning-effort", reasoning_effort
    ]

    # Run the process and capture output for progress
    env = os.environ.copy()
    # Prepend the src/ dir (parent of the installed homi package) so the
    # Michaelangelo subprocess resolves `from homi...` regardless of cwd.
    import homi
    src_root = str(Path(homi.__file__).resolve().parents[1])
    _existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{src_root}{os.pathsep}{_existing}" if _existing else src_root

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env=env
    )

    # Parse output for progress updates
    for line in iter(process.stdout.readline, ''):
        line = line.strip()
        if not line:
            continue

        # Parse progress from output
        if progress_callback:
            # Try to parse structured data from log line
            parsed = parse_exploration_log_line(line)
            if parsed:
                # Emit structured event for tree visualization
                progress_callback(parsed)

            # Also emit log message for backwards compatibility and display
            # Capture seed/run progress
            if "[Seed" in line or "[Run" in line:
                if "Starting" in line or "SUCCESS" in line or "FAILED" in line or "metrics:" in line or "API error" in line:
                    progress_callback({"type": "log", "message": line})
            # Also capture errors
            elif "ERROR" in line or "Error" in line:
                progress_callback({"type": "log", "message": line})

    process.wait()

    # Load and return the summary
    summary_path = output_dir_abs / "exploration_summary.json"
    if summary_path.exists():
        # Also copy to parent phase1 directory for app.py compatibility
        parent_summary = component_dir_abs / "phase1" / "exploration_summary.json"
        shutil.copy2(summary_path, parent_summary)

        with open(summary_path) as f:
            return json.load(f)

    return {"error": "Phase 1 failed to produce summary"}


def run_phase2(
    component_dir: Path,
    michaelangelo_dir: Path,
    sse_threshold: float = float('inf'),
    iou_threshold: float = 0.0,  # Deprecated, kept for backward compat
    additional_turns: int = 3,
    num_parallel: int = 8,
    model: str = "gemini/gemini-3-flash-preview",
    progress_callback: Optional[Callable[[dict], None]] = None
) -> dict:
    """
    Run Phase 2: Extended iteration on qualifying seeds.

    Args:
        component_dir: Path to component directory
        michaelangelo_dir: Path to michaelangelo installation
        sse_threshold: Maximum SSE from Phase 1 to qualify (lower is better, inf = all pass)
        iou_threshold: DEPRECATED - kept for backward compatibility
        additional_turns: Number of additional turns
        num_parallel: Number of parallel workers
        model: Model to use (unified format: provider/model-name)
            Examples:
            - "gemini/gemini-3-flash-preview" (default)
            - "anthropic/claude-sonnet-4.5"
            - "openai/gpt-5.2"
            - "qwen/qwen3-vl-235b-a22b-thinking"
        progress_callback: Optional callback for progress updates

    Returns:
        Extended iteration summary dict
    """
    # Use new multi-model script if available, fallback to gemini-specific
    phase2_script = michaelangelo_dir / "core" / "extended_iteration.py"
    if not phase2_script.exists():
        phase2_script = michaelangelo_dir / "core" / "gemini_extended_iteration.py"

    # Model-specific directories to prevent overwriting between models
    sanitized_model = _sanitize_model_name(model)
    phase1_dir = component_dir / "phase1" / f"benchmark_{sanitized_model}"
    output_dir = component_dir / "phase2" / f"benchmark_{sanitized_model}"

    # Use absolute paths to avoid nesting issues in subprocess
    component_dir_abs = Path(component_dir).resolve()
    phase1_dir_abs = Path(phase1_dir).resolve()
    output_dir_abs = Path(output_dir).resolve()

    cmd = [
        sys.executable, str(phase2_script),
        "--component-dir", str(component_dir_abs),
        "--phase1-dir", str(phase1_dir_abs),
        "--output-dir", str(output_dir_abs),
        "--sse-threshold", str(sse_threshold),
        "--additional-turns", str(additional_turns),
        "--num-parallel", str(num_parallel),
        "--model", model
    ]

    # Run the process
    env = os.environ.copy()
    # Prepend the src/ dir (parent of the installed homi package) so the
    # Michaelangelo subprocess resolves `from homi...` regardless of cwd.
    import homi
    src_root = str(Path(homi.__file__).resolve().parents[1])
    _existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{src_root}{os.pathsep}{_existing}" if _existing else src_root

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env=env
    )

    for line in iter(process.stdout.readline, ''):
        line = line.strip()
        if not line:
            continue

        if progress_callback:
            # Try to parse structured data from log line
            parsed = parse_exploration_log_line(line)
            if parsed:
                # Emit structured event for tree visualization
                progress_callback(parsed)

            # Also emit log message for backwards compatibility and display
            # Capture seed/run progress
            if "[Seed" in line or "[Run" in line:
                if "Starting" in line or "SUCCESS" in line or "FAILED" in line or "metrics:" in line or "API error" in line:
                    progress_callback({"type": "log", "message": line})
            # Also capture errors
            elif "ERROR" in line or "Error" in line:
                progress_callback({"type": "log", "message": line})

    process.wait()

    # Load and return the summary
    summary_path = output_dir_abs / "extended_exploration_summary.json"
    if summary_path.exists():
        # Also copy to parent phase2 directory for app.py compatibility
        parent_summary = component_dir_abs / "phase2" / "extended_exploration_summary.json"
        parent_summary.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(summary_path, parent_summary)

        with open(summary_path) as f:
            return json.load(f)

    return {"error": "Phase 2 failed to produce summary"}


def get_best_result(component_dir: Path, model: Optional[str] = None) -> dict:
    """
    Get the best result from Phase 2 (or Phase 1 if Phase 2 didn't run).

    Args:
        component_dir: Path to component directory
        model: Optional model to get results for. If None, searches all benchmark_* subdirs.

    Returns:
        Dict with best seed info, paths to GDS and script
    """
    component_dir = Path(component_dir)

    # Determine which directories to search
    if model:
        sanitized_model = _sanitize_model_name(model)
        phase2_dirs = [component_dir / "phase2" / f"benchmark_{sanitized_model}"]
        phase1_dirs = [component_dir / "phase1" / f"benchmark_{sanitized_model}"]
    else:
        # Search all benchmark_* subdirectories
        phase2_base = component_dir / "phase2"
        phase1_base = component_dir / "phase1"
        phase2_dirs = list(phase2_base.glob("benchmark_*")) if phase2_base.exists() else []
        phase1_dirs = list(phase1_base.glob("benchmark_*")) if phase1_base.exists() else []

        # Also check legacy non-benchmark structure for backwards compatibility
        if (phase2_base / "extended_exploration_summary.json").exists():
            phase2_dirs.append(phase2_base)
        if (phase1_base / "exploration_summary.json").exists():
            phase1_dirs.append(phase1_base)

    best_seed = None
    best_run_id = None
    best_iou = 0
    best_sse = float('inf')
    best_turn = None
    source_dir = None
    best_model = None

    # Try Phase 2 first - find best across all models
    for phase2_dir in phase2_dirs:
        phase2_summary = phase2_dir / "extended_exploration_summary.json"
        if not phase2_summary.exists():
            continue

        with open(phase2_summary) as f:
            summary = json.load(f)

        run_id = summary.get("best_run_by_sse") or summary.get("best_run_by_iou")
        seed = summary.get("best_seed_by_sse") or summary.get("best_seed_by_iou")
        sse = summary.get("best_final_sse", float('inf'))
        iou = summary.get("best_final_iou", 0)

        if run_id is not None and sse < best_sse:
            best_run_id = run_id
            best_seed = seed
            best_iou = iou
            best_sse = sse
            best_model = summary.get("model", phase2_dir.name)

            # Find the best turn from results
            for result in summary.get("results", []):
                if result.get("run_id") == run_id:
                    best_turn = result.get("final_turn", result.get("best_sse_turn", 5))
                    break

            # Directory is named run_XXX, not seed_XXX
            source_dir = phase2_dir / f"run_{best_run_id:03d}" / f"turn{best_turn}"

    # Fall back to Phase 1 if no Phase 2 results
    if source_dir is None or not source_dir.exists():
        for phase1_dir in phase1_dirs:
            phase1_summary = phase1_dir / "exploration_summary.json"
            if not phase1_summary.exists():
                continue

            with open(phase1_summary) as f:
                summary = json.load(f)

            # Get best run ID (directories are run_XXX format)
            run_id = summary.get("best_run_by_sse") or summary.get("best_run_by_iou")
            seed = summary.get("best_seed_by_sse") or summary.get("best_seed_by_iou")

            if run_id is not None:
                # Get metrics from the appropriate ranking
                ranked = summary.get("ranked_by_sse") or summary.get("ranked_by_iou", [])
                sse = ranked[0].get("final_sse", float('inf')) if ranked else float('inf')
                iou = ranked[0].get("final_iou", 0) if ranked else 0

                if sse < best_sse:
                    best_run_id = run_id
                    best_seed = seed
                    best_iou = iou
                    best_sse = sse
                    best_turn = 2
                    best_model = summary.get("model", phase1_dir.name)
                    # Directory is named run_XXX, not seed_XXX
                    source_dir = phase1_dir / f"run_{best_run_id:03d}" / "turn2"

    if not source_dir or not source_dir.exists():
        return {"error": f"No valid results found. Expected dir: {source_dir}"}

    # Find the GDS and script files
    gds_files = list(source_dir.glob("*.gds"))
    script_file = source_dir / "generated_component.py"
    raster_file = source_dir / "raster.png"
    overlay_file = source_dir / "overlay.png"

    return {
        "seed": best_seed,
        "iou": best_iou,
        "sse": best_sse,
        "turn": best_turn,
        "model": best_model,
        "gds_path": str(gds_files[0]) if gds_files else None,
        "script_path": str(script_file) if script_file.exists() else None,
        "raster_path": str(raster_file) if raster_file.exists() else None,
        "overlay_path": str(overlay_file) if overlay_file.exists() else None,
        "source_dir": str(source_dir)
    }


def collect_best_output(component_dir: Path, output_dir: Path) -> dict:
    """
    Copy the best result to the output directory.

    Args:
        component_dir: Path to component directory
        output_dir: Path to output directory

    Returns:
        Dict with paths to copied files
    """
    best = get_best_result(component_dir)

    if "error" in best:
        return best

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    result = {
        "seed": best["seed"],
        "iou": best["iou"],
        "sse": best.get("sse", float('inf')),
        "turn": best["turn"]
    }

    # Copy GDS
    if best.get("gds_path"):
        dest_gds = output_dir / "best.gds"
        shutil.copy2(best["gds_path"], dest_gds)
        result["gds_path"] = str(dest_gds)

    # Copy script
    if best.get("script_path"):
        dest_script = output_dir / "best.py"
        shutil.copy2(best["script_path"], dest_script)
        result["script_path"] = str(dest_script)

    # Copy raster
    if best.get("raster_path"):
        dest_raster = output_dir / "best_raster.png"
        shutil.copy2(best["raster_path"], dest_raster)
        result["raster_path"] = str(dest_raster)

    # Copy overlay
    if best.get("overlay_path"):
        dest_overlay = output_dir / "best_overlay.png"
        shutil.copy2(best["overlay_path"], dest_overlay)
        result["overlay_path"] = str(dest_overlay)

    # Save summary
    summary_path = output_dir / "summary.json"
    with open(summary_path, "w") as f:
        json.dump(result, f, indent=2)
    result["summary_path"] = str(summary_path)

    return result


def get_phase1_progress(component_dir: Path, model: Optional[str] = None) -> dict:
    """Get current progress of Phase 1 by checking run directories.

    Args:
        component_dir: Path to component directory
        model: Optional model to get progress for. If None, aggregates all models.

    Returns:
        Dict with completed count, total, and top results.
    """
    component_dir = Path(component_dir)
    phase1_base = component_dir / "phase1"
    if not phase1_base.exists():
        return {"completed": 0, "total": 0, "results": [], "models": []}

    # Determine which directories to search
    if model:
        sanitized_model = _sanitize_model_name(model)
        benchmark_dirs = [phase1_base / f"benchmark_{sanitized_model}"]
    else:
        benchmark_dirs = list(phase1_base.glob("benchmark_*"))
        # Also check legacy non-benchmark structure
        if (phase1_base / "exploration_summary.json").exists():
            benchmark_dirs.append(phase1_base)

    results = []
    models_found = set()

    for benchmark_dir in benchmark_dirs:
        if not benchmark_dir.exists():
            continue

        model_name = benchmark_dir.name if benchmark_dir.name.startswith("benchmark_") else "legacy"
        models_found.add(model_name)

        # Try run_* directories (new format)
        run_dirs = list(benchmark_dir.glob("run_*"))
        # Also check seed_* directories (legacy format)
        seed_dirs = list(benchmark_dir.glob("seed_*"))

        for run_dir in run_dirs + seed_dirs:
            summary_file = run_dir / "summary.json"
            if summary_file.exists():
                with open(summary_file) as f:
                    run_summary = json.load(f)
                    run_summary["model"] = model_name
                    results.append(run_summary)

    # Sort by SSE (turn2 if available) - lower is better
    results.sort(
        key=lambda x: x.get("turn2_metrics", {}).get("SSE", float('inf')) if x.get("turn2_metrics") else float('inf'),
        reverse=False
    )

    return {
        "completed": len(results),
        "total": 25,  # Default seed count
        "results": results[:10],  # Top 10
        "models": list(models_found)
    }


def get_phase2_progress(component_dir: Path, model: Optional[str] = None) -> dict:
    """Get current progress of Phase 2 by checking run directories.

    Args:
        component_dir: Path to component directory
        model: Optional model to get progress for. If None, aggregates all models.

    Returns:
        Dict with completed count, total, and top results.
    """
    component_dir = Path(component_dir)
    phase2_base = component_dir / "phase2"
    if not phase2_base.exists():
        return {"completed": 0, "total": 0, "results": [], "models": []}

    # Determine which directories to search
    if model:
        sanitized_model = _sanitize_model_name(model)
        benchmark_dirs = [phase2_base / f"benchmark_{sanitized_model}"]
    else:
        benchmark_dirs = list(phase2_base.glob("benchmark_*"))
        # Also check legacy non-benchmark structure
        if (phase2_base / "extended_exploration_summary.json").exists():
            benchmark_dirs.append(phase2_base)

    results = []
    models_found = set()
    total_dirs = 0

    for benchmark_dir in benchmark_dirs:
        if not benchmark_dir.exists():
            continue

        model_name = benchmark_dir.name if benchmark_dir.name.startswith("benchmark_") else "legacy"
        models_found.add(model_name)

        # Try run_* directories (new format)
        run_dirs = list(benchmark_dir.glob("run_*"))
        # Also check seed_* directories (legacy format)
        seed_dirs = list(benchmark_dir.glob("seed_*"))
        total_dirs += len(run_dirs) + len(seed_dirs)

        for run_dir in run_dirs + seed_dirs:
            summary_file = run_dir / "extended_summary.json"
            if summary_file.exists():
                with open(summary_file) as f:
                    run_summary = json.load(f)
                    run_summary["model"] = model_name
                    results.append(run_summary)

    # Sort by final SSE - lower is better
    results.sort(key=lambda x: x.get("final_sse", float('inf')), reverse=False)

    return {
        "completed": len(results),
        "total": total_dirs if total_dirs else 0,
        "results": results[:10],
        "models": list(models_found)
    }


def get_available_models(provider: Optional[str] = None) -> List[str]:
    """Get list of available models for GDS generation.

    Args:
        provider: Optional filter by provider ("gemini", "claude", "openai", "openrouter").

    Returns:
        List of model names in unified format (provider/model-name).

    Example:
        >>> get_available_models()
        ['gemini/gemini-3-flash-preview', 'anthropic/claude-sonnet-4.5', ...]

        >>> get_available_models("gemini")
        ['gemini/gemini-3-flash-preview', 'gemini/gemini-3-pro-preview', ...]
    """
    return list_models(provider)


def get_available_providers() -> List[str]:
    """Get list of available model providers.

    Returns:
        List of provider names.

    Example:
        >>> get_available_providers()
        ['gemini', 'claude', 'openai', 'openrouter']
    """
    return list_providers()


def get_model_info(model_name: str) -> Optional[dict]:
    """Get information about a specific model.

    Args:
        model_name: Unified model name (e.g., "anthropic/claude-sonnet-4.5").

    Returns:
        Dict with model capabilities, or None if model not found.

    Example:
        >>> info = get_model_info("anthropic/claude-sonnet-4.5")
        >>> info.supports_seed
        False
        >>> info.supports_thinking
        True
    """
    caps = get_model_capabilities(model_name)
    if caps is None:
        return None
    return {
        "supports_seed": caps.supports_seed,
        "supports_thinking": caps.supports_thinking,
        "supports_vision": caps.supports_vision,
        "max_tokens": caps.max_tokens,
    }
