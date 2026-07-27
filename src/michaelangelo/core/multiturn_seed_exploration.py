#!/usr/bin/env python3
"""
Multi-Turn Seed Exploration for GDS Component Generation

Combines seed exploration with multi-turn iteration:
- Tests multiple seeds/runs in parallel
- For each seed/run: Turn 1 generates, Turn 2 sees raster and improves
- Compares final results across all seeds/runs to find the best

Supports multiple AI providers via unified model client:
- Google Gemini (native seed support)
- Anthropic Claude (multiple runs for exploration)
- OpenAI GPT (multiple runs for exploration)
- OpenRouter models: Llama, Kimi, Qwen (native seed support)

Usage:
    python multiturn_seed_exploration.py \\
        --component-dir ./component \\
        --model gemini/gemini-3-flash-preview \\
        --base-seed 1333 \\
        --seed-range 12
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional, Tuple

# Load environment variables from .env (upward search / checkout / ~/.pixcell/env)
try:
    from homi.paths import load_env
    load_env()
except ImportError:
    pass  # dotenv not installed

from homi.model_client import (
    create_client,
    ModelClient,
    ModelConfig,
    VisionMessage,
    get_model_capabilities,
    supports_seed,
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
    # Try ```python ... ``` format first
    pattern = r"```python\s*(.*?)```"
    matches = re.findall(pattern, response_text, re.DOTALL)
    if matches:
        return max(matches, key=len).strip()

    # Fallback to ``` ... ``` with gdsfactory imports
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

        # Find most recent GDS file
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
    """Rasterize GDS using ABSOLUTE scaling and compare to target."""
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


def generate_calibration(
    component_dir: Path,
    calibrate_script: Path,
    target_image: Path,
    footprint_path: Path,
    calibration_path: Path
) -> bool:
    """Generate calibration file if it doesn't exist."""
    if calibration_path.exists():
        return True

    with open(footprint_path) as f:
        footprint = json.load(f)

    length_um = footprint["footprint_um"][0]
    width_um = footprint["footprint_um"][1]

    cmd = [
        sys.executable, str(calibrate_script),
        "--reference-image", str(target_image),
        "--footprint-length-um", str(length_um),
        "--footprint-width-um", str(width_um),
        "--out", str(calibration_path)
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return result.returncode == 0 and calibration_path.exists()
    except Exception as e:
        print(f"Failed to generate calibration: {e}")
        return False


def run_single_exploration(
    run_id: int,
    seed: Optional[int],
    target_bytes: bytes,
    catalog_text: str,
    footprint_text: str,
    original_prompt: str,
    iteration_prompt: str,
    output_dir: Path,
    target_image: Path,
    compare_script: Path,
    calibration_path: Path,
    client: ModelClient,
    model_id: str,
    model_supports_seed: bool,
    model_supports_thinking: bool,
    max_attempts: int = 3,
    reasoning_effort: str = "high"
) -> dict:
    """Run multi-turn exploration for a single seed/run.

    Args:
        run_id: Unique identifier for this run
        seed: Seed value (None for non-seed models)
        target_bytes: Target image bytes
        catalog_text: GDS catalog text
        footprint_text: Footprint JSON text
        original_prompt: Initial generation prompt
        iteration_prompt: Iteration prompt
        output_dir: Base output directory
        target_image: Path to target image
        compare_script: Path to comparison script
        calibration_path: Path to calibration JSON
        client: Model client instance
        model_id: Model ID for API calls
        model_supports_seed: Whether model supports seed parameter
        model_supports_thinking: Whether model supports thinking mode
        max_attempts: Max attempts per turn
        reasoning_effort: Thinking/reasoning effort level (high, medium, low)

    Returns:
        Dict with results for this run
    """
    run_dir = output_dir / f"run_{run_id:03d}"
    turn1_dir = run_dir / "turn1"
    turn2_dir = run_dir / "turn2"

    run_dir.mkdir(parents=True, exist_ok=True)
    turn1_dir.mkdir(exist_ok=True)
    turn2_dir.mkdir(exist_ok=True)

    seed_str = f"seed={seed}" if seed is not None else "no-seed"
    safe_print(f"[Run {run_id:03d}] Starting ({seed_str})")

    result = {
        "run_id": run_id,
        "seed": seed,
        "turn1_success": False,
        "turn2_success": False,
        "turn1_metrics": None,
        "turn2_metrics": None,
        "turn1_attempts": 0,
        "turn2_attempts": 0
    }

    # Build config
    # Note: max_tokens must be > thinking_budget for Claude models
    thinking_budget = 32000 if model_supports_thinking else None
    config = ModelConfig(
        temperature=1.0,
        max_tokens=64000 if model_supports_thinking else 16000,
        seed=seed if model_supports_seed else None,
        thinking_mode=reasoning_effort if model_supports_thinking else None,
        thinking_budget=thinking_budget,
    )

    # =========================================================================
    # TURN 1: Original prompt
    # =========================================================================
    turn1_text = f"""## GDSFactory Function Catalog (Reference)

{catalog_text}

---

## Device Footprint Constraint

{footprint_text}

---

## Task

{original_prompt}"""

    messages = [
        VisionMessage(
            role="user",
            text=turn1_text,
            images=[target_bytes],
            image_mime_types=["image/png"]
        )
    ]

    # Telemetry tracking for Turn 1
    turn1_start = time.time()
    turn1_attempts: List[AttemptRecord] = []
    turn1_usage: Optional[Dict[str, int]] = None
    turn1_thinking: Optional[str] = None
    turn1_exec_duration = 0.0

    response1_text = None
    gds1_path = None

    for attempt in range(1, max_attempts + 1):
        result["turn1_attempts"] = attempt
        attempt_record = AttemptRecord(attempt=attempt, timestamp=time.time())

        try:
            api_start = time.time()
            response1 = client.generate(messages, config, model_id)
            attempt_record.api_duration = time.time() - api_start

            response1_text = response1.text
            attempt_record.usage = response1.usage
            attempt_record.code_extracted = True

            # Capture usage and thinking content from successful API call
            if response1.usage:
                turn1_usage = response1.usage
            if response1.thinking_content:
                turn1_thinking = response1.thinking_content

        except Exception as e:
            safe_print(f"[Run {run_id:03d}] Turn 1 API error: {e}")
            attempt_record.failure_type = "api_error"
            attempt_record.error_message = str(e)[:500]
            turn1_attempts.append(attempt_record)
            continue

        code1 = extract_python_code(response1_text)
        if not code1:
            # Ask for proper code format
            attempt_record.code_extracted = False
            attempt_record.failure_type = "no_code_extracted"
            turn1_attempts.append(attempt_record)
            messages.append(VisionMessage(role="assistant", text=response1_text))
            messages.append(VisionMessage(
                role="user",
                text="Please provide the complete Python script in a ```python code block."
            ))
            continue

        script1_path = turn1_dir / "generated_component.py"
        script1_path.write_text(code1)

        exec_start = time.time()
        success1, msg1, gds1_path = execute_code(script1_path, turn1_dir)
        turn1_exec_duration = time.time() - exec_start

        if success1:
            attempt_record.success = True
            turn1_attempts.append(attempt_record)
            safe_print(f"[Run {run_id:03d}] Turn 1 SUCCESS (attempt {attempt})")
            break
        else:
            error_msg = extract_error_message(msg1)
            attempt_record.failure_type = "execution_error"
            attempt_record.error_message = error_msg[:500]
            turn1_attempts.append(attempt_record)
            messages.append(VisionMessage(role="assistant", text=response1_text))
            messages.append(VisionMessage(
                role="user",
                text=f"Error:\n{error_msg}\n\nPlease fix and provide the corrected script."
            ))

    # Save Turn 1 log
    if response1_text:
        (turn1_dir / "log.txt").write_text(f"Turn 1 Response:\n\n{response1_text}")

    if not gds1_path:
        safe_print(f"[Run {run_id:03d}] Turn 1 FAILED after {max_attempts} attempts")
        # Save telemetry even on failure
        _save_turn_telemetry(
            turn1_dir, 1, turn1_start, time.time(), turn1_attempts,
            0, turn1_usage, turn1_thinking, turn1_exec_duration, 0.0, None,
            model_id, client.provider_name
        )
        with open(run_dir / "summary.json", "w") as f:
            json.dump(result, f, indent=2)
        return result

    result["turn1_success"] = True

    # Rasterize Turn 1
    raster_start = time.time()
    raster1_path, metrics1 = rasterize_and_compare(
        gds1_path, turn1_dir, target_image, compare_script, calibration_path
    )
    turn1_raster_duration = time.time() - raster_start
    turn1_end = time.time()

    if metrics1:
        # Keep existing 3-field summary for backward compatibility
        result["turn1_metrics"] = {
            "IoU": metrics1.get("IoU"),
            "Dice": metrics1.get("Dice"),
            "SSE": metrics1.get("SSE")
        }
        safe_print(f"[Run {run_id:03d}] Turn 1 metrics: SSE={metrics1.get('SSE', 0):.0f}, IoU={metrics1['IoU']:.4f}")

    # Save Turn 1 telemetry
    _save_turn_telemetry(
        turn1_dir, 1, turn1_start, turn1_end, turn1_attempts,
        result["turn1_attempts"], turn1_usage, turn1_thinking,
        turn1_exec_duration, turn1_raster_duration, metrics1,
        model_id, client.provider_name
    )

    if not raster1_path:
        safe_print(f"[Run {run_id:03d}] Turn 1 rasterization failed, skipping Turn 2")
        with open(run_dir / "summary.json", "w") as f:
            json.dump(result, f, indent=2)
        return result

    # =========================================================================
    # TURN 2: Iteration with raster feedback
    # =========================================================================

    # Add model's Turn 1 response to history
    messages.append(VisionMessage(role="assistant", text=response1_text))

    # Load raster for Turn 2
    raster1_bytes = load_image_bytes(raster1_path)

    # Add Turn 2 content
    turn2_text = f"""Here is what your code rendered (the image above).

{iteration_prompt}"""

    messages.append(VisionMessage(
        role="user",
        text=turn2_text,
        images=[raster1_bytes],
        image_mime_types=["image/png"]
    ))

    # Telemetry tracking for Turn 2
    turn2_start = time.time()
    turn2_attempts: List[AttemptRecord] = []
    turn2_usage: Optional[Dict[str, int]] = None
    turn2_thinking: Optional[str] = None
    turn2_exec_duration = 0.0
    turn2_raster_duration = 0.0
    metrics2 = None

    response2_text = None
    gds2_path = None

    for attempt in range(1, max_attempts + 1):
        result["turn2_attempts"] = attempt
        attempt_record = AttemptRecord(attempt=attempt, timestamp=time.time())

        try:
            api_start = time.time()
            response2 = client.generate(messages, config, model_id)
            attempt_record.api_duration = time.time() - api_start

            response2_text = response2.text
            attempt_record.usage = response2.usage
            attempt_record.code_extracted = True

            # Capture usage and thinking content from successful API call
            if response2.usage:
                turn2_usage = response2.usage
            if response2.thinking_content:
                turn2_thinking = response2.thinking_content

        except Exception as e:
            safe_print(f"[Run {run_id:03d}] Turn 2 API error: {e}")
            attempt_record.failure_type = "api_error"
            attempt_record.error_message = str(e)[:500]
            turn2_attempts.append(attempt_record)
            continue

        code2 = extract_python_code(response2_text)
        if not code2:
            attempt_record.code_extracted = False
            attempt_record.failure_type = "no_code_extracted"
            turn2_attempts.append(attempt_record)
            messages.append(VisionMessage(role="assistant", text=response2_text))
            messages.append(VisionMessage(
                role="user",
                text="Please provide the complete improved Python script in a ```python code block."
            ))
            continue

        script2_path = turn2_dir / "generated_component.py"
        script2_path.write_text(code2)

        exec_start = time.time()
        success2, msg2, gds2_path = execute_code(script2_path, turn2_dir)
        turn2_exec_duration = time.time() - exec_start

        if success2:
            attempt_record.success = True
            turn2_attempts.append(attempt_record)
            safe_print(f"[Run {run_id:03d}] Turn 2 SUCCESS (attempt {attempt})")
            break
        else:
            error_msg = extract_error_message(msg2)
            attempt_record.failure_type = "execution_error"
            attempt_record.error_message = error_msg[:500]
            turn2_attempts.append(attempt_record)
            messages.append(VisionMessage(role="assistant", text=response2_text))
            messages.append(VisionMessage(
                role="user",
                text=f"Error:\n{error_msg}\n\nPlease fix and provide the corrected script."
            ))

    # Save Turn 2 log
    if response2_text:
        (turn2_dir / "log.txt").write_text(f"Turn 2 Response:\n\n{response2_text}")

    if gds2_path:
        result["turn2_success"] = True

        # Rasterize Turn 2
        raster_start = time.time()
        raster2_path, metrics2 = rasterize_and_compare(
            gds2_path, turn2_dir, target_image, compare_script, calibration_path
        )
        turn2_raster_duration = time.time() - raster_start

        if metrics2:
            # Keep existing 3-field summary for backward compatibility
            result["turn2_metrics"] = {
                "IoU": metrics2.get("IoU"),
                "Dice": metrics2.get("Dice"),
                "SSE": metrics2.get("SSE")
            }
            safe_print(f"[Run {run_id:03d}] Turn 2 metrics: SSE={metrics2.get('SSE', 0):.0f}, IoU={metrics2['IoU']:.4f}")
    else:
        safe_print(f"[Run {run_id:03d}] Turn 2 FAILED after {max_attempts} attempts")

    turn2_end = time.time()

    # Save Turn 2 telemetry
    _save_turn_telemetry(
        turn2_dir, 2, turn2_start, turn2_end, turn2_attempts,
        result["turn2_attempts"] if result["turn2_success"] else 0,
        turn2_usage, turn2_thinking,
        turn2_exec_duration, turn2_raster_duration, metrics2,
        model_id, client.provider_name
    )

    # Save run-level telemetry
    run_telemetry = {
        "run_id": run_id,
        "seed": seed,
        "model": model_id,
        "provider": client.provider_name,
        "turns": {
            "turn1": {
                "success": result["turn1_success"],
                "attempts": len(turn1_attempts),
                "usage": turn1_usage,
                "duration_seconds": round(turn1_end - turn1_start, 3) if turn1_end else None,
                "final_sse": metrics1.get("SSE") if metrics1 else None,
                "final_iou": metrics1.get("IoU") if metrics1 else None
            },
            "turn2": {
                "success": result["turn2_success"],
                "attempts": len(turn2_attempts),
                "usage": turn2_usage,
                "duration_seconds": round(turn2_end - turn2_start, 3),
                "final_sse": metrics2.get("SSE") if metrics2 else None,
                "final_iou": metrics2.get("IoU") if metrics2 else None
            }
        },
        "cumulative_usage": _sum_usage([turn1_usage, turn2_usage]),
        "total_api_calls": len(turn1_attempts) + len(turn2_attempts),
        "total_successful_turns": (1 if result["turn1_success"] else 0) + (1 if result["turn2_success"] else 0)
    }
    with open(run_dir / "run_telemetry.json", "w") as f:
        json.dump(run_telemetry, f, indent=2)

    # Save summary (existing format for backward compatibility)
    with open(run_dir / "summary.json", "w") as f:
        json.dump(result, f, indent=2)

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Multi-turn seed exploration for GDS component generation"
    )
    parser.add_argument("--component-dir", type=Path, required=True,
                        help="Path to component folder containing component.png, footprint.json, etc.")
    parser.add_argument("--target-image", default="component.png",
                        help="Target image filename (relative to component-dir)")
    parser.add_argument("--footprint", default="footprint.json",
                        help="Footprint JSON filename (relative to component-dir)")
    parser.add_argument("--prompt", default="prompt.md",
                        help="Prompt file (relative to component-dir)")
    parser.add_argument("--iteration-prompt", default="iteration_prompt.md",
                        help="Iteration prompt file (relative to component-dir)")
    parser.add_argument("--catalogue", default=None,
                        help="GDS catalogue file path")
    parser.add_argument("--calibration", default="calibration.json",
                        help="Calibration JSON filename (relative to component-dir)")
    parser.add_argument("--output-dir", default="multiturn_exploration",
                        help="Output directory name (relative to component-dir)")
    parser.add_argument("--base-seed", type=int, default=1333,
                        help="Base seed for exploration")
    parser.add_argument("--seed-range", type=int, default=12,
                        help="Range around base seed (+/-)")
    parser.add_argument("--num-parallel", type=int, default=8,
                        help="Number of parallel workers")
    parser.add_argument("--max-attempts", type=int, default=3,
                        help="Max attempts per turn")
    parser.add_argument("--model", default="gemini/gemini-3-flash-preview",
                        help="Model to use (e.g., gemini/gemini-3-flash-preview, anthropic/claude-sonnet-4.5)")
    parser.add_argument("--reasoning-effort", default="high",
                        choices=["high", "medium", "low"],
                        help="Reasoning/thinking effort level (default: high)")
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
    if not component_dir.exists():
        print(f"ERROR: Component directory not found: {component_dir}")
        sys.exit(1)

    target_image = component_dir / args.target_image
    footprint_path = component_dir / args.footprint
    prompt_path = component_dir / args.prompt
    iteration_prompt_path = component_dir / args.iteration_prompt
    calibration_path = component_dir / args.calibration
    output_dir = component_dir / args.output_dir

    # Find core scripts directory
    script_dir = Path(__file__).parent.resolve()
    compare_script = script_dir / "compare_absolute.py"
    calibrate_script = script_dir / "calibrate_boundary.py"

    # Find catalogue
    if args.catalogue:
        catalogue_path = Path(args.catalogue).resolve()
    else:
        catalogue_path = script_dir.parent / "reference" / "gds_factory_function_catalogue_extended.md"

    # Validate required files
    required_files = [
        (target_image, "Target image"),
        (footprint_path, "Footprint JSON"),
        (prompt_path, "Prompt file"),
        (iteration_prompt_path, "Iteration prompt file"),
        (catalogue_path, "GDS catalogue"),
        (compare_script, "compare_absolute.py"),
        (calibrate_script, "calibrate_boundary.py"),
    ]

    for path, name in required_files:
        if not path.exists():
            print(f"ERROR: {name} not found: {path}")
            sys.exit(1)

    print("=" * 70)
    print("Multi-Turn Exploration")
    print(f"Model: {args.model}")
    print(f"Component: {component_dir.name}")
    print(f"Base seed: {args.base_seed}, Range: +/-{args.seed_range}")
    print(f"Parallel workers: {args.num_parallel}")
    print("=" * 70)

    # Generate calibration if needed
    if not calibration_path.exists():
        print("\nGenerating calibration...")
        if not generate_calibration(
            component_dir, calibrate_script, target_image,
            footprint_path, calibration_path
        ):
            print("ERROR: Failed to generate calibration")
            sys.exit(1)
        print(f"Calibration saved to: {calibration_path}")

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate run list
    # For seed-supporting models: use seeds
    # For non-seed models: just run N times
    num_runs = 2 * args.seed_range + 1
    if model_supports_seed:
        runs = [
            (i, args.base_seed - args.seed_range + i)
            for i in range(num_runs)
        ]
        print(f"\nWill test {num_runs} seeds: {runs[0][1]} to {runs[-1][1]}")
    else:
        runs = [(i, None) for i in range(num_runs)]
        print(f"\nWill run {num_runs} independent explorations (no seed support)")

    # Load shared resources
    print("\nLoading resources...")
    target_bytes = load_image_bytes(target_image)
    catalog_text = load_text(catalogue_path)
    footprint_text = load_text(footprint_path)
    original_prompt = load_text(prompt_path)
    iteration_prompt = load_text(iteration_prompt_path)

    print(f"  Target: {target_image.name}")
    print(f"  Catalog: {len(catalog_text)} chars")
    print(f"  Footprint: {footprint_text.strip()}")

    print(f"\nStarting with {args.num_parallel} parallel workers...\n")
    start_time = datetime.now()

    # Run explorations in parallel
    results = []
    with ThreadPoolExecutor(max_workers=args.num_parallel) as executor:
        futures = {
            executor.submit(
                run_single_exploration,
                run_id=run_id,
                seed=seed,
                target_bytes=target_bytes,
                catalog_text=catalog_text,
                footprint_text=footprint_text,
                original_prompt=original_prompt,
                iteration_prompt=iteration_prompt,
                output_dir=output_dir,
                target_image=target_image,
                compare_script=compare_script,
                calibration_path=calibration_path,
                client=client,
                model_id=model_id,
                model_supports_seed=model_supports_seed,
                model_supports_thinking=model_supports_thinking,
                max_attempts=args.max_attempts,
                reasoning_effort=args.reasoning_effort
            ): run_id
            for run_id, seed in runs
        }

        for future in as_completed(futures):
            run_id = futures[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                safe_print(f"[Run {run_id:03d}] Exception: {e}")
                results.append({
                    "run_id": run_id,
                    "seed": None,
                    "turn1_success": False,
                    "turn2_success": False,
                    "turn1_metrics": None,
                    "turn2_metrics": None
                })

    # Sort by run_id
    results.sort(key=lambda x: x["run_id"])

    elapsed = datetime.now() - start_time

    # =========================================================================
    # SUMMARY
    # =========================================================================
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    turn1_successes = [r for r in results if r["turn1_success"]]
    turn2_successes = [r for r in results if r["turn2_success"]]

    print(f"\nTurn 1 Success: {len(turn1_successes)}/{len(results)}")
    print(f"Turn 2 Success: {len(turn2_successes)}/{len(results)}")
    print(f"Time: {elapsed}")

    # Calculate rankings
    ranked_results = []
    for r in results:
        if r["turn2_metrics"] and r["turn2_metrics"]["IoU"] is not None:
            entry = {
                "run_id": r["run_id"],
                "seed": r["seed"],
                "turn1": r["turn1_metrics"],
                "turn2": r["turn2_metrics"],
                "final_iou": r["turn2_metrics"]["IoU"],
                "final_dice": r["turn2_metrics"]["Dice"],
                "final_sse": r["turn2_metrics"].get("SSE", float('inf'))
            }

            if r["turn1_metrics"] and r["turn1_metrics"]["IoU"]:
                iou_change = (r["turn2_metrics"]["IoU"] - r["turn1_metrics"]["IoU"]) / r["turn1_metrics"]["IoU"] * 100
                dice_change = (r["turn2_metrics"]["Dice"] - r["turn1_metrics"]["Dice"]) / r["turn1_metrics"]["Dice"] * 100
                entry["improvement"] = {
                    "IoU": f"{'+' if iou_change > 0 else ''}{iou_change:.1f}%",
                    "Dice": f"{'+' if dice_change > 0 else ''}{dice_change:.1f}%"
                }
                if r["turn1_metrics"].get("SSE") and r["turn1_metrics"]["SSE"] > 0:
                    sse_change = (r["turn2_metrics"].get("SSE", 0) - r["turn1_metrics"]["SSE"]) / r["turn1_metrics"]["SSE"] * 100
                    entry["improvement"]["SSE"] = f"{'+' if sse_change > 0 else ''}{sse_change:.1f}%"

            ranked_results.append(entry)

    # Rank by SSE (lower is better)
    ranked_by_sse = sorted(ranked_results, key=lambda x: x["final_sse"], reverse=False)

    # Rank by IoU (higher is better)
    ranked_by_iou = sorted(ranked_results, key=lambda x: x["final_iou"], reverse=True)

    # Rank by Dice (higher is better)
    ranked_by_dice = sorted(ranked_results, key=lambda x: x["final_dice"], reverse=True)

    print("\n--- Top 5 by SSE (lower is better) ---")
    for i, r in enumerate(ranked_by_sse[:5], 1):
        sse_change = r.get("improvement", {}).get("SSE", "N/A")
        seed_str = f"seed={r['seed']}" if r['seed'] is not None else "no-seed"
        print(f"  {i}. Run {r['run_id']:03d} ({seed_str}): SSE={r['final_sse']:.0f} (change: {sse_change})")

    print("\n--- Top 5 by IoU (higher is better) ---")
    for i, r in enumerate(ranked_by_iou[:5], 1):
        improvement = r.get("improvement", {}).get("IoU", "N/A")
        seed_str = f"seed={r['seed']}" if r['seed'] is not None else "no-seed"
        print(f"  {i}. Run {r['run_id']:03d} ({seed_str}): IoU={r['final_iou']:.4f} (improvement: {improvement})")

    # Save exploration summary
    exploration_summary = {
        "model": args.model,
        "model_id": model_id,
        "provider": client.provider_name,
        "supports_seed": model_supports_seed,
        "supports_thinking": model_supports_thinking,
        "runs_tested": len(results),
        "turn1_successful": len(turn1_successes),
        "turn2_successful": len(turn2_successes),
        "elapsed_time": str(elapsed),
        # SSE-based rankings
        "best_run_by_sse": ranked_by_sse[0]["run_id"] if ranked_by_sse else None,
        "best_seed_by_sse": ranked_by_sse[0]["seed"] if ranked_by_sse else None,
        "ranked_by_sse": ranked_by_sse[:10],
        # IoU-based rankings
        "best_run_by_iou": ranked_by_iou[0]["run_id"] if ranked_by_iou else None,
        "best_seed_by_iou": ranked_by_iou[0]["seed"] if ranked_by_iou else None,
        "ranked_by_iou": ranked_by_iou[:10],
        "ranked_by_dice": ranked_by_dice[:10],
        "all_results": results
    }

    summary_path = output_dir / "exploration_summary.json"
    with open(summary_path, "w") as f:
        json.dump(exploration_summary, f, indent=2)

    print(f"\nExploration summary saved to: {summary_path}")

    # =========================================================================
    # AGGREGATE TELEMETRY SUMMARY
    # =========================================================================
    telemetry_summary = {
        "exploration_start_iso": start_time.isoformat(),
        "exploration_end_iso": datetime.now().isoformat(),
        "exploration_duration_seconds": round(elapsed.total_seconds(), 3),
        "model": args.model,
        "model_id": model_id,
        "provider": client.provider_name,
        "runs_total": len(results),
        "runs_successful": len(turn2_successes),
        "aggregate_usage": {
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_tokens": 0
        },
        "aggregate_timing": {
            "total_turn1_seconds": 0.0,
            "total_turn2_seconds": 0.0
        },
        "aggregate_attempts": {
            "total_api_calls": 0,
            "total_successful_turns": 0,
            "turn1_attempts_total": 0,
            "turn2_attempts_total": 0
        }
    }

    # Load and aggregate per-run telemetry
    for result in results:
        run_telem_path = output_dir / f"run_{result['run_id']:03d}" / "run_telemetry.json"
        if run_telem_path.exists():
            try:
                with open(run_telem_path) as f:
                    run_telem = json.load(f)

                # Aggregate usage
                cu = run_telem.get("cumulative_usage", {})
                telemetry_summary["aggregate_usage"]["total_input_tokens"] += cu.get("input_tokens", 0)
                telemetry_summary["aggregate_usage"]["total_output_tokens"] += cu.get("output_tokens", 0)
                telemetry_summary["aggregate_usage"]["total_tokens"] += cu.get("total_tokens", 0)

                # Aggregate attempts
                telemetry_summary["aggregate_attempts"]["total_api_calls"] += run_telem.get("total_api_calls", 0)
                telemetry_summary["aggregate_attempts"]["total_successful_turns"] += run_telem.get("total_successful_turns", 0)

                # Aggregate timing
                turns = run_telem.get("turns", {})
                if turns.get("turn1", {}).get("duration_seconds"):
                    telemetry_summary["aggregate_timing"]["total_turn1_seconds"] += turns["turn1"]["duration_seconds"]
                    telemetry_summary["aggregate_attempts"]["turn1_attempts_total"] += turns["turn1"].get("attempts", 0)
                if turns.get("turn2", {}).get("duration_seconds"):
                    telemetry_summary["aggregate_timing"]["total_turn2_seconds"] += turns["turn2"]["duration_seconds"]
                    telemetry_summary["aggregate_attempts"]["turn2_attempts_total"] += turns["turn2"].get("attempts", 0)

            except (json.JSONDecodeError, KeyError) as e:
                safe_print(f"Warning: Could not read telemetry for run {result['run_id']}: {e}")

    # Calculate averages
    if len(results) > 0:
        telemetry_summary["aggregate_usage"]["average_tokens_per_run"] = round(
            telemetry_summary["aggregate_usage"]["total_tokens"] / len(results), 1
        )
        telemetry_summary["aggregate_attempts"]["average_attempts_per_turn"] = round(
            telemetry_summary["aggregate_attempts"]["total_api_calls"] / (len(results) * 2), 2
        ) if len(results) > 0 else 0

    # Round timing values
    telemetry_summary["aggregate_timing"]["total_turn1_seconds"] = round(
        telemetry_summary["aggregate_timing"]["total_turn1_seconds"], 3
    )
    telemetry_summary["aggregate_timing"]["total_turn2_seconds"] = round(
        telemetry_summary["aggregate_timing"]["total_turn2_seconds"], 3
    )

    telemetry_path = output_dir / "telemetry_summary.json"
    with open(telemetry_path, "w") as f:
        json.dump(telemetry_summary, f, indent=2)

    print(f"Telemetry summary saved to: {telemetry_path}")
    print("=" * 70)

    return len(turn2_successes) > 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
