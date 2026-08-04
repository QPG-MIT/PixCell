#!/usr/bin/env python3
"""
Extended Iteration for GDS Component Generation (Phase 2)

Takes runs that passed threshold from Phase 1 and continues iterating
for additional turns (typically turns 3, 4, 5, etc.).

Supports multiple AI providers via unified model client:
- Google Gemini (native seed support)
- Anthropic Claude
- OpenAI GPT
- OpenRouter models: Llama, Kimi, Qwen

Usage:
    python extended_iteration.py \\
        --component-dir ./component \\
        --phase1-dir ./component/multiturn_exploration \\
        --model gemini/gemini-3-flash-preview \\
        --additional-turns 3
"""

import argparse
import json
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional, Tuple

from homi.model_client import (
    create_client,
    ModelClient,
    ModelConfig,
    VisionMessage,
    get_model_capabilities,
)

# Thread-safe print lock
print_lock = Lock()


# =============================================================================
# TELEMETRY DATA STRUCTURES
# =============================================================================

@dataclass
class AttemptRecord:
    """Record for a single API attempt within a turn."""
    attempt: int
    timestamp: float = 0.0
    api_duration: float = 0.0
    usage: Optional[Dict[str, int]] = None
    success: bool = False
    failure_type: Optional[str] = None
    error_message: Optional[str] = None
    code_extracted: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "attempt": self.attempt,
            "timestamp_iso": datetime.fromtimestamp(self.timestamp).isoformat() if self.timestamp else None,
            "api_duration_seconds": self.api_duration,
            "usage": self.usage,
            "success": self.success,
            "failure_type": self.failure_type,
            "error_message": self.error_message,
            "code_extracted": self.code_extracted
        }


def _sum_usage(usage_list: List[Optional[Dict[str, int]]]) -> Dict[str, int]:
    """Sum token usage across multiple API calls."""
    total = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    for u in usage_list:
        if u:
            for k in total:
                total[k] += u.get(k, 0)
    return total


def _save_turn_telemetry(
    turn_dir: Path,
    turn_num: int,
    turn_start: float,
    turn_end: float,
    attempts: List[AttemptRecord],
    successful_attempt: int,
    final_usage: Optional[Dict[str, int]],
    thinking_content: Optional[str],
    exec_duration: float,
    raster_duration: float,
    full_metrics: Optional[Dict],
    model_id: str,
    provider: str
) -> None:
    """Save telemetry data for a single turn."""
    # Save telemetry.json
    telemetry = {
        "turn": turn_num,
        "timestamp": {
            "start_iso": datetime.fromtimestamp(turn_start).isoformat(),
            "end_iso": datetime.fromtimestamp(turn_end).isoformat(),
            "duration_seconds": round(turn_end - turn_start, 3)
        },
        "api": {
            "model_id": model_id,
            "provider": provider,
            "successful_attempt": successful_attempt,
            "total_attempts": len(attempts),
            "usage": final_usage,
            "thinking_content_length": len(thinking_content) if thinking_content else None
        },
        "execution": {
            "script_execution_seconds": round(exec_duration, 3),
            "rasterization_seconds": round(raster_duration, 3)
        },
        "full_metrics": full_metrics
    }
    with open(turn_dir / "telemetry.json", "w") as f:
        json.dump(telemetry, f, indent=2)

    # Save attempts.json
    attempts_data = {
        "turn": turn_num,
        "successful_attempt": successful_attempt,
        "attempts": [a.to_dict() for a in attempts],
        "cumulative_usage": _sum_usage([a.usage for a in attempts])
    }
    with open(turn_dir / "attempts.json", "w") as f:
        json.dump(attempts_data, f, indent=2)

    # Save thinking.txt if available
    if thinking_content:
        (turn_dir / "thinking.txt").write_text(thinking_content)


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def safe_print(message: str):
    """Thread-safe printing."""
    with print_lock:
        print(message, flush=True)


def load_image_bytes(path: Path) -> bytes:
    """Load image as bytes."""
    with open(path, "rb") as f:
        return f.read()


def load_text(path: Path) -> str:
    """Load text file."""
    with open(path, "r") as f:
        return f.read()


def extract_python_code(response_text: str) -> str | None:
    """Extract Python code from response."""
    pattern = r"```python\s*(.*?)```"
    matches = re.findall(pattern, response_text, re.DOTALL)
    if matches:
        return max(matches, key=len).strip()
    pattern = r"```\s*(.*?)```"
    matches = re.findall(pattern, response_text, re.DOTALL)
    for match in matches:
        if "import" in match and ("gdsfactory" in match or "gf." in match):
            return match.strip()
    return None


def extract_error_message(error_output: str) -> str:
    """Extract the actual error message from a Python traceback."""
    lines = error_output.strip().split('\n')
    error_lines = []
    for i, line in enumerate(lines):
        if any(err in line for err in ['Error:', 'Exception:', 'error:', 'ValueError', 'TypeError',
                                         'AttributeError', 'KeyError', 'ImportError', 'NameError',
                                         'RuntimeError', 'IndexError', 'FileNotFoundError']):
            error_lines = lines[i:]
            break
    if error_lines:
        return '\n'.join(error_lines)[:1500]
    last_lines = lines[-10:] if len(lines) > 10 else lines
    return '\n'.join(last_lines)[:1500]


def execute_code(script_path: Path, output_dir: Path) -> Tuple[bool, str, Path | None]:
    """Execute script and find GDS file."""
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(output_dir),
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode != 0:
            output = result.stdout + result.stderr
            return False, f"Execution failed:\n{output}", None

        gds_files = list(output_dir.glob("*.gds"))
        if gds_files:
            return True, "Success", max(gds_files, key=lambda p: p.stat().st_mtime)
        return False, "No GDS file produced", None

    except subprocess.TimeoutExpired:
        return False, "Timeout", None
    except Exception as e:
        return False, str(e), None


def rasterize_and_compare(
    gds_path: Path,
    output_dir: Path,
    target_image: Path,
    compare_script: Path,
    calibration_path: Path
) -> Tuple[Path | None, dict | None]:
    """Rasterize GDS and compare to target."""
    raster_path = output_dir / "raster.png"
    metrics_path = output_dir / "metrics.json"
    diff_path = output_dir / "diff.png"
    overlay_path = output_dir / "overlay.png"

    cmd = [
        sys.executable, str(compare_script),
        "--gds", str(gds_path),
        "--target", str(target_image),
        "--calibration", str(calibration_path),
        "--out-raster", str(raster_path),
        "--out-diff", str(diff_path),
        "--out-overlay", str(overlay_path),
        "--out-metrics", str(metrics_path),
        "--layer", "1",
        "--datatype", "0"
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode == 0 and raster_path.exists() and metrics_path.exists():
            with open(metrics_path) as f:
                metrics = json.load(f)
            return raster_path, metrics
        return None, None
    except Exception:
        return None, None


def get_qualifying_runs(
    phase1_dir: Path,
    sse_threshold: float = float('inf')
) -> List[dict]:
    """Find runs from Phase 1 that passed threshold.

    Args:
        phase1_dir: Path to Phase 1 output directory
        sse_threshold: Maximum SSE to qualify (lower is better, inf = all pass)

    Returns:
        List of qualifying run info dicts
    """
    summary_path = phase1_dir / "exploration_summary.json"
    if not summary_path.exists():
        print(f"Phase 1 summary not found: {summary_path}")
        return []

    with open(summary_path) as f:
        summary = json.load(f)

    qualifying = []
    for result in summary.get("all_results", []):
        if not result.get("turn2_success"):
            continue

        turn2_metrics = result.get("turn2_metrics", {})
        sse = turn2_metrics.get("SSE", float('inf'))
        iou = turn2_metrics.get("IoU", 0)

        if sse <= sse_threshold:
            qualifying.append({
                "run_id": result["run_id"],
                "seed": result.get("seed"),
                "phase1_sse": sse,
                "phase1_iou": iou,
                "phase1_dice": turn2_metrics.get("Dice", 0)
            })

    return qualifying


def run_extended_iteration(
    run_info: dict,
    phase1_dir: Path,
    output_dir: Path,
    target_bytes: bytes,
    target_image: Path,
    catalog_text: str,
    footprint_text: str,
    iteration_prompt: str,
    compare_script: Path,
    calibration_path: Path,
    client: ModelClient,
    model_id: str,
    model_supports_seed: bool,
    model_supports_thinking: bool,
    additional_turns: int = 3,
    max_attempts: int = 3
) -> dict:
    """Continue iteration for a qualifying run.

    Args:
        run_info: Info about the run from Phase 1
        phase1_dir: Path to Phase 1 output
        output_dir: Path to Phase 2 output
        target_bytes: Target image bytes
        target_image: Path to target image
        catalog_text: GDS catalog text
        footprint_text: Footprint JSON text
        iteration_prompt: Iteration prompt
        compare_script: Path to comparison script
        calibration_path: Path to calibration JSON
        client: Model client instance
        model_id: Model ID for API calls
        model_supports_seed: Whether model supports seed
        model_supports_thinking: Whether model supports thinking
        additional_turns: Number of additional turns
        max_attempts: Max attempts per turn

    Returns:
        Dict with extended iteration results
    """
    run_id = run_info["run_id"]
    seed = run_info.get("seed")
    safe_print(f"[Run {run_id:03d}] Starting extended iteration (Phase 1 SSE: {run_info['phase1_sse']:.0f})")

    # Setup directories
    run_dir = output_dir / f"run_{run_id:03d}"
    run_dir.mkdir(parents=True, exist_ok=True)

    # Find Phase 1 Turn 2 files
    phase1_run_dir = phase1_dir / f"run_{run_id:03d}"
    phase1_turn2_code = phase1_run_dir / "turn2" / "generated_component.py"
    phase1_turn2_raster = phase1_run_dir / "turn2" / "raster.png"

    if not phase1_turn2_code.exists() or not phase1_turn2_raster.exists():
        safe_print(f"[Run {run_id:03d}] Phase 1 Turn 2 files not found")
        return {
            "run_id": run_id,
            "seed": seed,
            "phase1_sse": run_info["phase1_sse"],
            "phase1_iou": run_info["phase1_iou"],
            "phase1_dice": run_info["phase1_dice"],
            "trajectory": [],
            "final_turn": 2,
            "final_sse": run_info["phase1_sse"],
            "final_iou": run_info["phase1_iou"],
            "final_dice": run_info["phase1_dice"],
            "early_stopped": True,
            "stop_reason": "Phase 1 files not found"
        }

    result = {
        "run_id": run_id,
        "seed": seed,
        "phase1_sse": run_info["phase1_sse"],
        "phase1_iou": run_info["phase1_iou"],
        "phase1_dice": run_info["phase1_dice"],
        "trajectory": [],
        "final_turn": 2,
        "final_sse": run_info["phase1_sse"],
        "final_iou": run_info["phase1_iou"],
        "final_dice": run_info["phase1_dice"],
        # Best metrics across all turns (for final ranking)
        "best_sse": run_info["phase1_sse"],
        "best_sse_turn": 2,
        "best_iou": run_info["phase1_iou"],
        "best_iou_turn": 2,
        "early_stopped": False,
        "stop_reason": None
    }

    # Load Phase 1 Turn 2 state
    current_code = phase1_turn2_code.read_text()
    current_raster_bytes = load_image_bytes(phase1_turn2_raster)

    # Build config
    # Note: max_tokens must be > thinking_budget for Claude models
    thinking_budget = 32000 if model_supports_thinking else None
    config = ModelConfig(
        temperature=1.0,
        max_tokens=64000 if model_supports_thinking else 16000,
        seed=seed if model_supports_seed else None,
        thinking_mode="high" if model_supports_thinking else None,
        thinking_budget=thinking_budget,
    )

    # Track metrics for early stopping
    prev_sse = run_info["phase1_sse"]
    consecutive_increases = 0

    # Telemetry tracking for the entire run
    run_start = time.time()
    all_turn_telemetry: List[Dict] = []

    # =========================================================================
    # Extended turns (3, 4, 5, ...)
    # =========================================================================
    for turn_num in range(3, 3 + additional_turns):
        turn_dir = run_dir / f"turn{turn_num}"
        turn_dir.mkdir(exist_ok=True)

        # Telemetry tracking for this turn
        turn_start = time.time()
        turn_attempts: List[AttemptRecord] = []
        turn_usage: Optional[Dict[str, int]] = None
        turn_thinking: Optional[str] = None
        turn_exec_duration = 0.0
        turn_raster_duration = 0.0
        turn_successful_attempt = 0

        safe_print(f"[Run {run_id:03d}] Starting Turn {turn_num}")

        # Build message with current raster and iteration prompt
        messages = [
            VisionMessage(
                role="user",
                text=f"""## GDSFactory Function Catalog (Reference)

{catalog_text}

---

## Device Footprint Constraint

{footprint_text}

---

## Current Code (from previous turn)

```python
{current_code}
```

---

## Current Raster Output

(See the second image below)
""",
                images=[target_bytes],
                image_mime_types=["image/png"]
            ),
            VisionMessage(
                role="user",
                text=f"""The image above shows what your current code rendered.
The first image is the target device you need to match.

{iteration_prompt}

This is Turn {turn_num} of the iteration process. Please analyze carefully and provide an improved version.""",
                images=[current_raster_bytes],
                image_mime_types=["image/png"]
            )
        ]

        response_text = None
        gds_path = None

        for attempt in range(1, max_attempts + 1):
            attempt_record = AttemptRecord(attempt=attempt, timestamp=time.time())

            try:
                api_start = time.time()
                response = client.generate(messages, config, model_id)
                attempt_record.api_duration = time.time() - api_start

                response_text = response.text
                attempt_record.usage = response.usage
                attempt_record.code_extracted = True

                # Capture usage and thinking content
                if response.usage:
                    turn_usage = response.usage
                if response.thinking_content:
                    turn_thinking = response.thinking_content

            except Exception as e:
                safe_print(f"[Run {run_id:03d}] Turn {turn_num} API error: {e}")
                attempt_record.failure_type = "api_error"
                attempt_record.error_message = str(e)[:500]
                turn_attempts.append(attempt_record)
                continue

            code = extract_python_code(response_text)
            if not code:
                attempt_record.code_extracted = False
                attempt_record.failure_type = "no_code_extracted"
                turn_attempts.append(attempt_record)
                messages.append(VisionMessage(role="assistant", text=response_text))
                messages.append(VisionMessage(
                    role="user",
                    text="Please provide the complete improved Python script in a ```python code block."
                ))
                continue

            script_path = turn_dir / "generated_component.py"
            script_path.write_text(code)

            exec_start = time.time()
            success, msg, gds_path = execute_code(script_path, turn_dir)
            turn_exec_duration = time.time() - exec_start

            if success:
                attempt_record.success = True
                turn_successful_attempt = attempt
                turn_attempts.append(attempt_record)
                safe_print(f"[Run {run_id:03d}] Turn {turn_num} SUCCESS (attempt {attempt})")
                current_code = code
                break
            else:
                error_msg = extract_error_message(msg)
                attempt_record.failure_type = "execution_error"
                attempt_record.error_message = error_msg[:500]
                turn_attempts.append(attempt_record)
                messages.append(VisionMessage(role="assistant", text=response_text))
                messages.append(VisionMessage(
                    role="user",
                    text=f"Error:\n{error_msg}\n\nPlease fix and provide the corrected script."
                ))

        # Save log
        if response_text:
            (turn_dir / "log.txt").write_text(f"Turn {turn_num} Response:\n\n{response_text}")

        if not gds_path:
            safe_print(f"[Run {run_id:03d}] Turn {turn_num} FAILED")
            # Save telemetry even on failure
            turn_end = time.time()
            _save_turn_telemetry(
                turn_dir, turn_num, turn_start, turn_end, turn_attempts,
                0, turn_usage, turn_thinking, turn_exec_duration, 0.0, None,
                model_id, client.provider_name
            )
            all_turn_telemetry.append({
                "turn": turn_num, "success": False, "attempts": len(turn_attempts),
                "usage": turn_usage, "duration_seconds": round(turn_end - turn_start, 3)
            })
            result["early_stopped"] = True
            result["stop_reason"] = f"Turn {turn_num} failed"
            break

        # Rasterize and compare
        raster_start = time.time()
        raster_path, metrics = rasterize_and_compare(
            gds_path, turn_dir, target_image, compare_script, calibration_path
        )
        turn_raster_duration = time.time() - raster_start
        turn_end = time.time()

        if not raster_path or not metrics:
            safe_print(f"[Run {run_id:03d}] Turn {turn_num} rasterization failed")
            _save_turn_telemetry(
                turn_dir, turn_num, turn_start, turn_end, turn_attempts,
                turn_successful_attempt, turn_usage, turn_thinking,
                turn_exec_duration, turn_raster_duration, None,
                model_id, client.provider_name
            )
            all_turn_telemetry.append({
                "turn": turn_num, "success": False, "attempts": len(turn_attempts),
                "usage": turn_usage, "duration_seconds": round(turn_end - turn_start, 3)
            })
            result["early_stopped"] = True
            result["stop_reason"] = f"Turn {turn_num} rasterization failed"
            break

        sse = metrics.get("SSE", float('inf'))
        iou = metrics.get("IoU", 0)
        dice = metrics.get("Dice", 0)

        # Save turn telemetry with full metrics
        _save_turn_telemetry(
            turn_dir, turn_num, turn_start, turn_end, turn_attempts,
            turn_successful_attempt, turn_usage, turn_thinking,
            turn_exec_duration, turn_raster_duration, metrics,
            model_id, client.provider_name
        )
        all_turn_telemetry.append({
            "turn": turn_num, "success": True, "attempts": len(turn_attempts),
            "usage": turn_usage, "duration_seconds": round(turn_end - turn_start, 3),
            "sse": sse, "iou": iou
        })

        # Update trajectory with full metrics (keeping backward compatibility with 3 fields)
        result["trajectory"].append({
            "turn": turn_num,
            "SSE": sse,
            "IoU": iou,
            "Dice": dice
        })

        result["final_turn"] = turn_num
        result["final_sse"] = sse
        result["final_iou"] = iou
        result["final_dice"] = dice

        # Track best metrics across all turns (for final ranking)
        if sse < result["best_sse"]:
            result["best_sse"] = sse
            result["best_sse_turn"] = turn_num
        if iou > result["best_iou"]:
            result["best_iou"] = iou
            result["best_iou_turn"] = turn_num

        safe_print(f"[Run {run_id:03d}] Turn {turn_num} metrics: SSE={sse:.0f}, IoU={iou:.4f}")

        # Update current raster for next iteration
        current_raster_bytes = load_image_bytes(raster_path)

        # Check for early stopping (SSE increased for 2 consecutive turns)
        if sse > prev_sse:
            consecutive_increases += 1
            if consecutive_increases >= 2:
                safe_print(f"[Run {run_id:03d}] Early stopping: SSE increased for 2 consecutive turns")
                result["early_stopped"] = True
                result["stop_reason"] = "SSE increased for 2 consecutive turns"
                break
        else:
            consecutive_increases = 0

        prev_sse = sse

    run_end = time.time()

    # Save run-level telemetry
    run_telemetry = {
        "run_id": run_id,
        "seed": seed,
        "model": model_id,
        "provider": client.provider_name,
        "phase1_sse": run_info["phase1_sse"],
        "phase1_iou": run_info["phase1_iou"],
        "run_duration_seconds": round(run_end - run_start, 3),
        "turns": all_turn_telemetry,
        "cumulative_usage": _sum_usage([t.get("usage") for t in all_turn_telemetry]),
        "total_api_calls": sum(t.get("attempts", 0) for t in all_turn_telemetry),
        "total_successful_turns": sum(1 for t in all_turn_telemetry if t.get("success"))
    }
    with open(run_dir / "run_telemetry.json", "w") as f:
        json.dump(run_telemetry, f, indent=2)

    # Save run summary (existing format for backward compatibility)
    with open(run_dir / "extended_summary.json", "w") as f:
        json.dump(result, f, indent=2)

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Extended iteration for GDS component generation (Phase 2)"
    )
    parser.add_argument("--component-dir", type=Path, required=True,
                        help="Path to component folder")
    parser.add_argument("--phase1-dir", type=Path, default=None,
                        help="Path to Phase 1 output directory")
    parser.add_argument("--target-image", default="component.png",
                        help="Target image filename")
    parser.add_argument("--footprint", default="footprint.json",
                        help="Footprint JSON filename")
    parser.add_argument("--iteration-prompt", default="iteration_prompt.md",
                        help="Iteration prompt file")
    parser.add_argument("--catalogue", default=None,
                        help="GDS catalogue file path")
    parser.add_argument("--calibration", default="calibration.json",
                        help="Calibration JSON filename")
    parser.add_argument("--output-dir", default="extended_iteration",
                        help="Output directory name")
    parser.add_argument("--sse-threshold", type=float, default=float('inf'),
                        help="Max SSE from Phase 1 to qualify (default: all)")
    parser.add_argument("--additional-turns", type=int, default=3,
                        help="Number of additional turns")
    parser.add_argument("--num-parallel", type=int, default=4,
                        help="Number of parallel workers")
    parser.add_argument("--max-attempts", type=int, default=3,
                        help="Max attempts per turn")
    parser.add_argument("--model", default="gemini/gemini-3-flash-preview",
                        help="Model to use")
    args = parser.parse_args()

    # Create model client
    print(f"Creating client for model: {args.model}")
    try:
        client, model_id = create_client(args.model)
    except ValueError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    # Check model capabilities
    caps = get_model_capabilities(args.model)
    model_supports_seed = caps.supports_seed
    model_supports_thinking = caps.supports_thinking

    print(f"  Provider: {client.provider_name}")
    print(f"  Model ID: {model_id}")
    print(f"  Supports seed: {model_supports_seed}")
    print(f"  Supports thinking: {model_supports_thinking}")

    # Resolve paths
    component_dir = args.component_dir.resolve()
    phase1_dir = (args.phase1_dir or component_dir / "multiturn_exploration").resolve()
    output_dir = component_dir / args.output_dir

    target_image = component_dir / args.target_image
    footprint_path = component_dir / args.footprint
    iteration_prompt_path = component_dir / args.iteration_prompt
    calibration_path = component_dir / args.calibration

    # Find core scripts directory
    script_dir = Path(__file__).parent.resolve()
    compare_script = script_dir / "compare_absolute.py"

    # Find catalogue
    if args.catalogue:
        catalogue_path = Path(args.catalogue).resolve()
    else:
        catalogue_path = script_dir.parent / "reference" / "gds_factory_function_catalogue_extended.md"

    # Validate required files
    required_files = [
        (target_image, "Target image"),
        (footprint_path, "Footprint JSON"),
        (iteration_prompt_path, "Iteration prompt file"),
        (calibration_path, "Calibration JSON"),
        (compare_script, "compare_absolute.py"),
        (phase1_dir / "exploration_summary.json", "Phase 1 summary"),
    ]

    for path, name in required_files:
        if not path.exists():
            print(f"ERROR: {name} not found: {path}")
            sys.exit(1)

    print("=" * 70)
    print("Extended Iteration (Phase 2)")
    print(f"Model: {args.model}")
    print(f"SSE Threshold: {args.sse_threshold}")
    print(f"Additional Turns: {args.additional_turns}")
    print("=" * 70)

    # Find qualifying runs
    print("\nFinding runs that passed threshold...")
    qualifying_runs = get_qualifying_runs(phase1_dir, args.sse_threshold)

    if not qualifying_runs:
        print(f"No runs found with SSE <= {args.sse_threshold}")
        print(f"Check Phase 1 output: {phase1_dir}")
        sys.exit(1)

    print(f"Found {len(qualifying_runs)} qualifying runs:")
    for r in qualifying_runs[:10]:
        seed_str = f"seed={r['seed']}" if r['seed'] is not None else "no-seed"
        print(f"  Run {r['run_id']:03d} ({seed_str}): SSE={r['phase1_sse']:.0f}, IoU={r['phase1_iou']:.4f}")

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load resources
    print("\nLoading resources...")
    target_bytes = load_image_bytes(target_image)
    catalog_text = load_text(catalogue_path) if catalogue_path.exists() else ""
    footprint_text = load_text(footprint_path)
    iteration_prompt = load_text(iteration_prompt_path)

    print(f"\nStarting extended iteration with {args.num_parallel} workers...\n")
    start_time = datetime.now()

    # Run in parallel
    results = []
    with ThreadPoolExecutor(max_workers=args.num_parallel) as executor:
        futures = {
            executor.submit(
                run_extended_iteration,
                run_info=run_info,
                phase1_dir=phase1_dir,
                output_dir=output_dir,
                target_bytes=target_bytes,
                target_image=target_image,
                catalog_text=catalog_text,
                footprint_text=footprint_text,
                iteration_prompt=iteration_prompt,
                compare_script=compare_script,
                calibration_path=calibration_path,
                client=client,
                model_id=model_id,
                model_supports_seed=model_supports_seed,
                model_supports_thinking=model_supports_thinking,
                additional_turns=args.additional_turns,
                max_attempts=args.max_attempts
            ): run_info["run_id"]
            for run_info in qualifying_runs
        }

        for future in as_completed(futures):
            run_id = futures[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                safe_print(f"[Run {run_id:03d}] Exception: {e}")

    results.sort(key=lambda x: x["run_id"])
    elapsed = datetime.now() - start_time

    # =========================================================================
    # SUMMARY
    # =========================================================================
    print("\n" + "=" * 70)
    print("EXTENDED ITERATION SUMMARY")
    print("=" * 70)

    print(f"\nRuns processed: {len(results)}")
    print(f"Time: {elapsed}")

    # Find best results (using best_sse across all turns, not final_sse)
    completed = [r for r in results if not r["early_stopped"]]
    best_by_sse = min(results, key=lambda x: x.get("best_sse", x.get("final_sse", float('inf')))) if results else None
    best_by_iou = max(results, key=lambda x: x.get("best_iou", x.get("final_iou", 0))) if results else None

    if best_by_sse:
        seed_str = f"seed={best_by_sse['seed']}" if best_by_sse['seed'] is not None else "no-seed"
        best_sse_val = best_by_sse.get("best_sse", best_by_sse.get("final_sse", 0))
        best_sse_turn = best_by_sse.get("best_sse_turn", best_by_sse.get("final_turn", 0))
        print(f"\nBest by SSE: Run {best_by_sse['run_id']:03d} ({seed_str})")
        print(f"  Best SSE: {best_sse_val:.0f} at Turn {best_sse_turn}")
        print(f"  Final SSE: {best_by_sse['final_sse']:.0f} at Turn {best_by_sse['final_turn']}")
        print(f"  Best IoU: {best_by_sse.get('best_iou', best_by_sse.get('final_iou', 0)):.4f}")

    print("\n--- All Results (sorted by Best SSE) ---")
    sorted_results = sorted(results, key=lambda x: x.get("best_sse", x.get("final_sse", float('inf'))))
    for r in sorted_results:
        status = "early stopped" if r["early_stopped"] else "completed"
        seed_str = f"seed={r['seed']}" if r['seed'] is not None else "no-seed"
        best_sse_val = r.get("best_sse", r.get("final_sse", 0))
        best_sse_turn = r.get("best_sse_turn", r.get("final_turn", 0))
        print(f"  Run {r['run_id']:03d} ({seed_str}): Best SSE={best_sse_val:.0f} at T{best_sse_turn} (final T{r['final_turn']}, {status})")

    # Save summary
    summary = {
        "model": args.model,
        "model_id": model_id,
        "provider": client.provider_name,
        "supports_seed": model_supports_seed,
        "supports_thinking": model_supports_thinking,
        "sse_threshold": args.sse_threshold,
        "additional_turns": args.additional_turns,
        "runs_processed": len(results),
        "runs_completed": len(completed),
        "elapsed_time": str(elapsed),
        "best_run_by_sse": best_by_sse["run_id"] if best_by_sse else None,
        "best_seed_by_sse": best_by_sse["seed"] if best_by_sse else None,
        # Use best_sse (best across all turns), not final_sse
        "best_final_sse": best_by_sse.get("best_sse", best_by_sse.get("final_sse")) if best_by_sse else None,
        "best_final_iou": best_by_iou.get("best_iou", best_by_iou.get("final_iou")) if best_by_iou else None,
        "results": results
    }

    summary_path = output_dir / "extended_exploration_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\nSummary saved to: {summary_path}")

    # Aggregate telemetry from all runs
    all_run_telemetries = []
    total_input_tokens = 0
    total_output_tokens = 0
    total_api_calls = 0
    total_failed_attempts = 0
    total_successful_attempts = 0
    turns_with_thinking = 0
    total_turns = 0

    for result in results:
        run_telem_path = output_dir / f"run_{result['run_id']:03d}" / "run_telemetry.json"
        if run_telem_path.exists():
            try:
                with open(run_telem_path) as f:
                    run_telem = json.load(f)
                all_run_telemetries.append(run_telem)

                # Aggregate usage
                if run_telem.get("cumulative_usage"):
                    total_input_tokens += run_telem["cumulative_usage"].get("input_tokens", 0)
                    total_output_tokens += run_telem["cumulative_usage"].get("output_tokens", 0)

                # Aggregate attempt counts
                total_api_calls += run_telem.get("total_api_calls", 0)
                total_failed_attempts += run_telem.get("total_failed_attempts", 0)
                total_successful_attempts += run_telem.get("total_successful_attempts", 0)

                # Count thinking content
                turns_with_thinking += run_telem.get("turns_with_thinking", 0)
                total_turns += run_telem.get("total_turns", 0)
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Warning: Could not read telemetry from {run_telem_path}: {e}")

    telemetry_summary = {
        "phase": "phase2_extended_iteration",
        "model": args.model,
        "timestamp": {
            "start_iso": start_time.isoformat(),
            "end_iso": datetime.now().isoformat(),
            "duration_seconds": elapsed.total_seconds()
        },
        "runs": {
            "total": len(results),
            "completed": len(completed),
            "with_telemetry": len(all_run_telemetries)
        },
        "aggregate_usage": {
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "total_tokens": total_input_tokens + total_output_tokens
        },
        "aggregate_attempts": {
            "total_api_calls": total_api_calls,
            "total_failed_attempts": total_failed_attempts,
            "total_successful_attempts": total_successful_attempts,
            "failure_rate": total_failed_attempts / total_api_calls if total_api_calls > 0 else 0
        },
        "thinking_content": {
            "total_turns": total_turns,
            "turns_with_thinking": turns_with_thinking,
            "thinking_rate": turns_with_thinking / total_turns if total_turns > 0 else 0
        },
        "per_run_telemetry": all_run_telemetries
    }

    telemetry_path = output_dir / "telemetry_summary.json"
    with open(telemetry_path, "w") as f:
        json.dump(telemetry_summary, f, indent=2)

    print(f"Telemetry summary saved to: {telemetry_path}")
    print("=" * 70)

    return len(results) > 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
