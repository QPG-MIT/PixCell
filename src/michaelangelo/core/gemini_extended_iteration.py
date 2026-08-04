#!/usr/bin/env python3
"""
Extended Multi-Turn Iteration with Progressive Filtering

Phase 2: Takes seeds that passed IoU threshold from Phase 1 and
continues iterating for additional turns (turns 3, 4, 5).

Features:
- Loads Phase 1 results and filters by IoU threshold
- Continues conversation from turn 2
- Tracks IoU trajectory
- Early stops if IoU drops for 2 consecutive turns

Uses Gemini API with configurable model and thinking level.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from threading import Lock

from google import genai
from google.genai import types

# Thread-safe print lock
print_lock = Lock()


def safe_print(message: str):
    """Thread-safe printing."""
    with print_lock:
        print(message, flush=True)


def load_image_bytes(path: Path) -> bytes:
    with open(path, "rb") as f:
        return f.read()


def load_text(path: Path) -> str:
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


def execute_code(script_path: Path, output_dir: Path) -> tuple[bool, str, Path | None]:
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


def rasterize_and_compare(gds_path: Path, output_dir: Path, target_image: Path,
                          compare_script: Path, calibration_path: Path) -> tuple[Path | None, dict | None]:
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


def run_extended_iteration(
    seed: int,
    phase1_result: dict,
    target_bytes: bytes,
    catalog_text: str,
    footprint_text: str,
    original_prompt: str,
    iteration_prompt: str,
    output_dir: Path,
    phase1_dir: Path,
    target_image: Path,
    compare_script: Path,
    calibration_path: Path,
    api_key: str,
    model: str,
    additional_turns: int = 3,
    max_attempts: int = 3
) -> dict:
    """Continue iteration from Phase 1 for a qualifying seed."""

    seed_dir = output_dir / f"seed_{seed}"
    seed_dir.mkdir(parents=True, exist_ok=True)

    phase1_sse = phase1_result.get("final_sse", float('inf'))
    safe_print(f"[Seed {seed}] Starting extended iteration (SSE={phase1_sse:.0f}, IoU={phase1_result['final_iou']:.4f})")

    result = {
        "seed": seed,
        "phase1_iou": phase1_result["final_iou"],
        "phase1_dice": phase1_result["final_dice"],
        "phase1_sse": phase1_sse,
        "trajectory": [
            {"turn": 1, "IoU": phase1_result["turn1"]["IoU"], "Dice": phase1_result["turn1"]["Dice"], "SSE": phase1_result["turn1"].get("SSE")},
            {"turn": 2, "IoU": phase1_result["turn2"]["IoU"], "Dice": phase1_result["turn2"]["Dice"], "SSE": phase1_result["turn2"].get("SSE")}
        ],
        "final_turn": 2,
        "final_iou": phase1_result["final_iou"],
        "final_dice": phase1_result["final_dice"],
        "final_sse": phase1_sse,
        # Best metrics across all turns (for final ranking)
        "best_sse": phase1_sse,
        "best_sse_turn": 2,
        "best_iou": phase1_result["final_iou"],
        "best_iou_turn": 2,
        "early_stopped": False,
        "stop_reason": None
    }

    # Initialize client
    client = genai.Client(api_key=api_key)

    # Configuration with seed and high thinking
    config = types.GenerateContentConfig(
        temperature=1.0,
        seed=seed,
        thinking_config=types.ThinkingConfig(thinking_level="high")
    )

    # Rebuild conversation history from Phase 1
    # Turn 1: Original prompt
    turn1_content = types.Content(
        role="user",
        parts=[
            types.Part.from_bytes(data=target_bytes, mime_type="image/png"),
            types.Part.from_text(text=f"""## GDSFactory Function Catalog (Reference)

{catalog_text}

---

## Device Footprint Constraint

{footprint_text}

---

## Task

{original_prompt}""")
        ]
    )

    # Load Turn 1 response
    phase1_seed_dir = phase1_dir / f"seed_{seed}"
    turn1_log = phase1_seed_dir / "turn1" / "log.txt"

    if turn1_log.exists():
        turn1_response_text = turn1_log.read_text().replace("Turn 1 Response:\n\n", "")
    else:
        safe_print(f"[Seed {seed}] Missing turn1 log, cannot continue")
        return result

    # Turn 2: Iteration with raster
    turn1_raster = phase1_seed_dir / "turn1" / "raster.png"
    if not turn1_raster.exists():
        safe_print(f"[Seed {seed}] Missing turn1 raster, cannot continue")
        return result

    turn1_raster_bytes = load_image_bytes(turn1_raster)

    turn2_content = types.Content(
        role="user",
        parts=[
            types.Part.from_bytes(data=turn1_raster_bytes, mime_type="image/png"),
            types.Part.from_text(text=f"""Here is what your code rendered (the image above).

{iteration_prompt}""")
        ]
    )

    # Load Turn 2 response
    turn2_log = phase1_seed_dir / "turn2" / "log.txt"
    if turn2_log.exists():
        turn2_response_text = turn2_log.read_text().replace("Turn 2 Response:\n\n", "")
    else:
        safe_print(f"[Seed {seed}] Missing turn2 log, cannot continue")
        return result

    # Build history
    history = [
        turn1_content,
        types.Content(role="model", parts=[types.Part.from_text(text=turn1_response_text)]),
        turn2_content,
        types.Content(role="model", parts=[types.Part.from_text(text=turn2_response_text)])
    ]

    # Track for early stopping (based on SSE - stop if SSE increases)
    consecutive_increases = 0
    previous_sse = phase1_sse
    current_raster_path = phase1_seed_dir / "turn2" / "raster.png"

    # =========================================================================
    # Extended Turns (3, 4, 5, ...)
    # =========================================================================
    for turn_num in range(3, 3 + additional_turns):
        turn_dir = seed_dir / f"turn{turn_num}"
        turn_dir.mkdir(exist_ok=True)

        safe_print(f"[Seed {seed}] Starting Turn {turn_num}")

        # Load current raster
        if not current_raster_path.exists():
            safe_print(f"[Seed {seed}] Missing raster for turn {turn_num}, stopping")
            result["early_stopped"] = True
            result["stop_reason"] = f"Missing raster at turn {turn_num}"
            break

        current_raster_bytes = load_image_bytes(current_raster_path)

        # Add iteration request
        turn_content = types.Content(
            role="user",
            parts=[
                types.Part.from_bytes(data=current_raster_bytes, mime_type="image/png"),
                types.Part.from_text(text=f"""Here is what your code rendered (the image above).

{iteration_prompt}""")
            ]
        )
        history.append(turn_content)

        # Try to generate and execute
        response_text = None
        gds_path = None

        for attempt in range(1, max_attempts + 1):
            try:
                response = client.models.generate_content(model=model, contents=history, config=config)
                response_text = response.text
            except Exception as e:
                safe_print(f"[Seed {seed}] Turn {turn_num} API error: {e}")
                continue

            code = extract_python_code(response_text)
            if not code:
                history.append(types.Content(role="model", parts=[types.Part.from_text(text=response_text)]))
                history.append(types.Content(role="user", parts=[types.Part.from_text(
                    text="Please provide the complete Python script in a ```python code block.")]))
                continue

            script_path = turn_dir / "generated_component.py"
            script_path.write_text(code)

            success, msg, gds_path = execute_code(script_path, turn_dir)

            if success:
                safe_print(f"[Seed {seed}] Turn {turn_num} SUCCESS (attempt {attempt})")
                break
            else:
                error_msg = extract_error_message(msg)
                history.append(types.Content(role="model", parts=[types.Part.from_text(text=response_text)]))
                history.append(types.Content(role="user", parts=[types.Part.from_text(
                    text=f"Error:\n{error_msg}\n\nPlease fix and provide the corrected script.")]))

        # Save log
        if response_text:
            (turn_dir / "log.txt").write_text(f"Turn {turn_num} Response:\n\n{response_text}")

        if not gds_path:
            safe_print(f"[Seed {seed}] Turn {turn_num} FAILED after {max_attempts} attempts")
            result["early_stopped"] = True
            result["stop_reason"] = f"Failed to generate valid code at turn {turn_num}"
            break

        # Add model response to history for next turn
        history.append(types.Content(role="model", parts=[types.Part.from_text(text=response_text)]))

        # Rasterize and compare
        raster_path, metrics = rasterize_and_compare(gds_path, turn_dir, target_image,
                                                      compare_script, calibration_path)

        if not raster_path or not metrics:
            safe_print(f"[Seed {seed}] Turn {turn_num} rasterization failed")
            result["early_stopped"] = True
            result["stop_reason"] = f"Rasterization failed at turn {turn_num}"
            break

        current_iou = metrics.get("IoU", 0)
        current_dice = metrics.get("Dice", 0)
        current_sse = metrics.get("SSE", float('inf'))

        result["trajectory"].append({
            "turn": turn_num,
            "IoU": current_iou,
            "Dice": current_dice,
            "SSE": current_sse
        })
        result["final_turn"] = turn_num
        result["final_iou"] = current_iou
        result["final_dice"] = current_dice
        result["final_sse"] = current_sse

        # Track best metrics across all turns (for final ranking)
        if current_sse < result["best_sse"]:
            result["best_sse"] = current_sse
            result["best_sse_turn"] = turn_num
        if current_iou > result["best_iou"]:
            result["best_iou"] = current_iou
            result["best_iou_turn"] = turn_num

        safe_print(f"[Seed {seed}] Turn {turn_num} metrics: SSE={current_sse:.0f}, IoU={current_iou:.4f}")

        # Check for early stopping (2 consecutive SSE increases = quality getting worse)
        if current_sse > previous_sse:
            consecutive_increases += 1
            if consecutive_increases >= 2:
                safe_print(f"[Seed {seed}] Early stopping: SSE increased for 2 consecutive turns")
                result["early_stopped"] = True
                result["stop_reason"] = "SSE increased for 2 consecutive turns"
                break
        else:
            consecutive_increases = 0

        previous_sse = current_sse
        current_raster_path = raster_path

    # Save extended summary
    with open(seed_dir / "extended_summary.json", "w") as f:
        json.dump(result, f, indent=2)

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Extended multi-turn iteration for GDS component generation (Phase 2)"
    )
    parser.add_argument("--component-dir", type=Path, required=True,
                        help="Path to component folder")
    parser.add_argument("--phase1-dir", type=Path, required=True,
                        help="Path to Phase 1 results directory (multiturn_seeds)")
    parser.add_argument("--output-dir", default="extended_iteration",
                        help="Output directory name (relative to component-dir)")
    parser.add_argument("--prompt", default="prompt.md",
                        help="Prompt file (relative to component-dir)")
    parser.add_argument("--iteration-prompt", default="iteration_prompt.md",
                        help="Iteration prompt file (relative to component-dir)")
    parser.add_argument("--catalogue", default=None,
                        help="GDS catalogue file path")
    parser.add_argument("--footprint", default="footprint.json",
                        help="Footprint JSON filename (relative to component-dir)")
    parser.add_argument("--target-image", default="component.png",
                        help="Target image filename (relative to component-dir)")
    parser.add_argument("--calibration", default="calibration.json",
                        help="Calibration JSON filename (relative to component-dir)")
    parser.add_argument("--iou-threshold", type=float, default=0.0,
                        help="DEPRECATED: Use --sse-threshold instead. Minimum IoU from Phase 1 to qualify.")
    parser.add_argument("--sse-threshold", type=float, default=float('inf'),
                        help="Maximum SSE from Phase 1 to qualify (lower is better, default=inf means all pass)")
    parser.add_argument("--additional-turns", type=int, default=3,
                        help="Number of additional turns (3, 4, 5, ...)")
    parser.add_argument("--max-attempts", type=int, default=3,
                        help="Max attempts per turn")
    parser.add_argument("--num-parallel", type=int, default=8,
                        help="Number of parallel workers")
    parser.add_argument("--model", default="gemini-3-flash-preview",
                        help="Gemini model to use")
    args = parser.parse_args()

    # Check API key
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY environment variable not set")
        print("Please set it with: export GEMINI_API_KEY=your_key")
        sys.exit(1)

    # Resolve paths
    component_dir = args.component_dir.resolve()
    if not component_dir.exists():
        print(f"ERROR: Component directory not found: {component_dir}")
        sys.exit(1)

    # Handle phase1-dir - can be absolute or relative to component-dir
    if args.phase1_dir.is_absolute():
        phase1_dir = args.phase1_dir.resolve()
    else:
        phase1_dir = (component_dir / args.phase1_dir).resolve()

    phase1_summary = phase1_dir / "exploration_summary.json"
    if not phase1_summary.exists():
        print(f"ERROR: Phase 1 summary not found at {phase1_summary}")
        print("Run gemini_multiturn_seed_exploration.py first!")
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
        (calibration_path, "Calibration JSON"),
        (catalogue_path, "GDS catalogue"),
        (compare_script, "compare_absolute.py"),
    ]

    for path, name in required_files:
        if not path.exists():
            print(f"ERROR: {name} not found: {path}")
            sys.exit(1)

    print("=" * 70)
    print("Extended Multi-Turn Iteration - Phase 2")
    print(f"Model: {args.model}")
    print(f"SSE Threshold: {args.sse_threshold} (lower is better)")
    print(f"Additional Turns: {args.additional_turns}")
    print(f"Parallel workers: {args.num_parallel}")
    print("=" * 70)

    # Load Phase 1 results
    with open(phase1_summary) as f:
        phase1_data = json.load(f)

    # Filter seeds by SSE threshold (lower is better)
    # Prefer ranked_by_sse if available, fall back to ranked_by_iou for backward compat
    ranking_source = phase1_data.get("ranked_by_sse") or phase1_data.get("ranked_by_iou", [])

    qualifying_seeds = []
    for result in ranking_source:
        # Use SSE if available, otherwise convert IoU (approximate)
        result_sse = result.get("final_sse", float('inf'))
        if result_sse <= args.sse_threshold:
            qualifying_seeds.append(result)

    print(f"\nSeeds passing SSE <= {args.sse_threshold:.0f} threshold: {len(qualifying_seeds)}")
    for s in qualifying_seeds:
        sse = s.get('final_sse', 'N/A')
        iou = s.get('final_iou', 0)
        sse_str = f"{sse:.0f}" if isinstance(sse, (int, float)) else str(sse)
        print(f"  Seed {s['seed']}: SSE={sse_str}, IoU={iou:.4f}")

    if not qualifying_seeds:
        print("No seeds qualify for extended iteration!")
        return False

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load shared resources
    print("\nLoading resources...")
    target_bytes = load_image_bytes(target_image)
    catalog_text = load_text(catalogue_path)
    footprint_text = load_text(footprint_path)
    original_prompt = load_text(prompt_path)
    iteration_prompt = load_text(iteration_prompt_path)

    print(f"\nStarting extended iteration on {len(qualifying_seeds)} seeds...\n")
    start_time = datetime.now()

    # Run in parallel
    results = []
    with ThreadPoolExecutor(max_workers=args.num_parallel) as executor:
        futures = {
            executor.submit(
                run_extended_iteration,
                seed=s["seed"],
                phase1_result=s,
                target_bytes=target_bytes,
                catalog_text=catalog_text,
                footprint_text=footprint_text,
                original_prompt=original_prompt,
                iteration_prompt=iteration_prompt,
                output_dir=output_dir,
                phase1_dir=phase1_dir,
                target_image=target_image,
                compare_script=compare_script,
                calibration_path=calibration_path,
                api_key=api_key,
                model=args.model,
                additional_turns=args.additional_turns,
                max_attempts=args.max_attempts
            ): s["seed"]
            for s in qualifying_seeds
        }

        for future in as_completed(futures):
            seed = futures[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                safe_print(f"[Seed {seed}] Exception: {e}")
                results.append({
                    "seed": seed,
                    "error": str(e)
                })

    # Sort by seed
    results.sort(key=lambda x: x.get("seed", 0))

    elapsed = datetime.now() - start_time

    # =========================================================================
    # SUMMARY
    # =========================================================================
    print("\n" + "=" * 70)
    print("EXTENDED ITERATION SUMMARY")
    print("=" * 70)

    print(f"\nTime: {elapsed}")
    print(f"Seeds processed: {len(results)}")

    # Show trajectory for each seed (SSE-based)
    print("\n--- SSE Trajectory (lower is better) ---")
    for r in results:
        if "trajectory" in r:
            traj = " -> ".join([f"T{t['turn']}:{t.get('SSE', 'N/A'):.0f}" if isinstance(t.get('SSE'), (int, float)) else f"T{t['turn']}:N/A" for t in r["trajectory"]])
            sse_change = ((r.get("final_sse", 0) - r.get("phase1_sse", 0)) / r.get("phase1_sse", 1) * 100) if r.get("phase1_sse", 0) > 0 else 0
            status = " (early stopped)" if r.get("early_stopped") else ""
            print(f"  Seed {r['seed']}: {traj} [{sse_change:+.1f}%]{status}")

    # Rank by best SSE across all turns (lower is better) - PRIMARY METRIC
    valid_results = [r for r in results if "final_sse" in r]
    ranked_by_sse = sorted(valid_results, key=lambda x: x.get("best_sse", x.get("final_sse", float('inf'))), reverse=False)

    # Also rank by best IoU for backward compatibility
    ranked_by_iou = sorted(valid_results, key=lambda x: x.get("best_iou", x.get("final_iou", 0)), reverse=True)

    print("\n--- Final Rankings by Best SSE (lower is better) ---")
    for i, r in enumerate(ranked_by_sse[:5], 1):
        best_sse = r.get("best_sse", r.get("final_sse", 0))
        best_turn = r.get("best_sse_turn", r.get("final_turn", 0))
        sse_change = ((best_sse - r.get("phase1_sse", 0)) / r.get("phase1_sse", 1) * 100) if r.get("phase1_sse", 0) > 0 else 0
        print(f"  {i}. Seed {r['seed']}: Best SSE={best_sse:.0f} at T{best_turn} (from {r.get('phase1_sse', 0):.0f}, {sse_change:+.1f}%)")

    # Save summary
    summary = {
        "model": args.model,
        "thinking_level": "high",
        "sse_threshold": args.sse_threshold,
        "iou_threshold": args.iou_threshold,  # Kept for backward compat
        "additional_turns": args.additional_turns,
        "seeds_processed": len(results),
        "elapsed_time": str(elapsed),
        # SSE-based best (primary metric) - uses best across all turns
        "best_seed": ranked_by_sse[0]["seed"] if ranked_by_sse else None,
        "best_final_sse": ranked_by_sse[0].get("best_sse", ranked_by_sse[0].get("final_sse")) if ranked_by_sse else None,
        # IoU-based for backward compatibility - uses best across all turns
        "best_final_iou": ranked_by_iou[0].get("best_iou", ranked_by_iou[0].get("final_iou")) if ranked_by_iou else None,
        "results": results
    }

    summary_path = output_dir / "extended_exploration_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\nSummary saved to: {summary_path}")
    print("=" * 70)

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
