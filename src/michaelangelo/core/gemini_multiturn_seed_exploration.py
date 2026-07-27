#!/usr/bin/env python3
"""
Multi-Turn Seed Exploration for GDS Component Generation

Combines seed exploration with multi-turn iteration:
- Tests multiple seeds in parallel
- For each seed: Turn 1 generates, Turn 2 sees raster and improves
- Compares final results across all seeds to find the best

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

        # Find most recent GDS file
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


def generate_calibration(component_dir: Path, calibrate_script: Path, target_image: Path,
                         footprint_path: Path, calibration_path: Path):
    """Generate calibration file if it doesn't exist."""
    if calibration_path.exists():
        return True

    # Load footprint
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


def run_seed_multiturn(
    seed: int,
    target_bytes: bytes,
    catalog_text: str,
    footprint_text: str,
    original_prompt: str,
    iteration_prompt: str,
    output_dir: Path,
    target_image: Path,
    compare_script: Path,
    calibration_path: Path,
    api_key: str,
    model: str,
    max_attempts: int = 3
) -> dict:
    """Run multi-turn exploration for a single seed."""

    seed_dir = output_dir / f"seed_{seed}"
    turn1_dir = seed_dir / "turn1"
    turn2_dir = seed_dir / "turn2"

    seed_dir.mkdir(parents=True, exist_ok=True)
    turn1_dir.mkdir(exist_ok=True)
    turn2_dir.mkdir(exist_ok=True)

    safe_print(f"[Seed {seed}] Starting multi-turn exploration")

    result = {
        "seed": seed,
        "turn1_success": False,
        "turn2_success": False,
        "turn1_metrics": None,
        "turn2_metrics": None,
        "turn1_attempts": 0,
        "turn2_attempts": 0
    }

    # Initialize client
    client = genai.Client(api_key=api_key)

    # Configuration with seed and high thinking
    config = types.GenerateContentConfig(
        temperature=1.0,
        seed=seed,
        thinking_config=types.ThinkingConfig(thinking_level="high")
    )

    # =========================================================================
    # TURN 1: Original prompt
    # =========================================================================
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

    history = [turn1_content]
    response1_text = None
    gds1_path = None

    for attempt in range(1, max_attempts + 1):
        result["turn1_attempts"] = attempt
        try:
            response1 = client.models.generate_content(model=model, contents=history, config=config)
            response1_text = response1.text
        except Exception as e:
            safe_print(f"[Seed {seed}] Turn 1 API error: {e}")
            continue

        code1 = extract_python_code(response1_text)
        if not code1:
            history.append(types.Content(role="model", parts=[types.Part.from_text(text=response1_text)]))
            history.append(types.Content(role="user", parts=[types.Part.from_text(
                text="Please provide the complete Python script in a ```python code block.")]))
            continue

        script1_path = turn1_dir / "generated_component.py"
        script1_path.write_text(code1)

        success1, msg1, gds1_path = execute_code(script1_path, turn1_dir)

        if success1:
            safe_print(f"[Seed {seed}] Turn 1 SUCCESS (attempt {attempt})")
            break
        else:
            error_msg = extract_error_message(msg1)
            history.append(types.Content(role="model", parts=[types.Part.from_text(text=response1_text)]))
            history.append(types.Content(role="user", parts=[types.Part.from_text(
                text=f"Error:\n{error_msg}\n\nPlease fix and provide the corrected script.")]))

    # Save Turn 1 log
    if response1_text:
        (turn1_dir / "log.txt").write_text(f"Turn 1 Response:\n\n{response1_text}")

    if not gds1_path:
        safe_print(f"[Seed {seed}] Turn 1 FAILED after {max_attempts} attempts")
        with open(seed_dir / "summary.json", "w") as f:
            json.dump(result, f, indent=2)
        return result

    result["turn1_success"] = True

    # Rasterize Turn 1
    raster1_path, metrics1 = rasterize_and_compare(gds1_path, turn1_dir, target_image,
                                                     compare_script, calibration_path)
    if metrics1:
        result["turn1_metrics"] = {"IoU": metrics1.get("IoU"), "Dice": metrics1.get("Dice"), "SSE": metrics1.get("SSE")}
        safe_print(f"[Seed {seed}] Turn 1 metrics: SSE={metrics1.get('SSE', 0):.0f}, IoU={metrics1['IoU']:.4f}")

    if not raster1_path:
        safe_print(f"[Seed {seed}] Turn 1 rasterization failed, skipping Turn 2")
        with open(seed_dir / "summary.json", "w") as f:
            json.dump(result, f, indent=2)
        return result

    # =========================================================================
    # TURN 2: Iteration with raster feedback
    # =========================================================================

    # Add model's Turn 1 response to history
    history.append(types.Content(role="model", parts=[types.Part.from_text(text=response1_text)]))

    # Load raster for Turn 2
    raster1_bytes = load_image_bytes(raster1_path)

    # Add Turn 2 content
    turn2_content = types.Content(
        role="user",
        parts=[
            types.Part.from_bytes(data=raster1_bytes, mime_type="image/png"),
            types.Part.from_text(text=f"""Here is what your code rendered (the image above).

{iteration_prompt}""")
        ]
    )
    history.append(turn2_content)

    response2_text = None
    gds2_path = None

    for attempt in range(1, max_attempts + 1):
        result["turn2_attempts"] = attempt
        try:
            response2 = client.models.generate_content(model=model, contents=history, config=config)
            response2_text = response2.text
        except Exception as e:
            safe_print(f"[Seed {seed}] Turn 2 API error: {e}")
            continue

        code2 = extract_python_code(response2_text)
        if not code2:
            history.append(types.Content(role="model", parts=[types.Part.from_text(text=response2_text)]))
            history.append(types.Content(role="user", parts=[types.Part.from_text(
                text="Please provide the complete improved Python script in a ```python code block.")]))
            continue

        script2_path = turn2_dir / "generated_component.py"
        script2_path.write_text(code2)

        success2, msg2, gds2_path = execute_code(script2_path, turn2_dir)

        if success2:
            safe_print(f"[Seed {seed}] Turn 2 SUCCESS (attempt {attempt})")
            break
        else:
            error_msg = extract_error_message(msg2)
            history.append(types.Content(role="model", parts=[types.Part.from_text(text=response2_text)]))
            history.append(types.Content(role="user", parts=[types.Part.from_text(
                text=f"Error:\n{error_msg}\n\nPlease fix and provide the corrected script.")]))

    # Save Turn 2 log
    if response2_text:
        (turn2_dir / "log.txt").write_text(f"Turn 2 Response:\n\n{response2_text}")

    if gds2_path:
        result["turn2_success"] = True

        # Rasterize Turn 2
        raster2_path, metrics2 = rasterize_and_compare(gds2_path, turn2_dir, target_image,
                                                         compare_script, calibration_path)
        if metrics2:
            result["turn2_metrics"] = {"IoU": metrics2.get("IoU"), "Dice": metrics2.get("Dice"), "SSE": metrics2.get("SSE")}
            safe_print(f"[Seed {seed}] Turn 2 metrics: SSE={metrics2.get('SSE', 0):.0f}, IoU={metrics2['IoU']:.4f}")
    else:
        safe_print(f"[Seed {seed}] Turn 2 FAILED after {max_attempts} attempts")

    # Save summary
    with open(seed_dir / "summary.json", "w") as f:
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
                        help="GDS catalogue file path (default: reference/gds_factory_function_catalogue_extended.md)")
    parser.add_argument("--calibration", default="calibration.json",
                        help="Calibration JSON filename (relative to component-dir)")
    parser.add_argument("--output-dir", default="multiturn_seeds",
                        help="Output directory name (relative to component-dir)")
    parser.add_argument("--base-seed", type=int, default=1333,
                        help="Base seed for exploration")
    parser.add_argument("--seed-range", type=int, default=12,
                        help="Range around base seed (+/-)")
    parser.add_argument("--num-parallel", type=int, default=8,
                        help="Number of parallel workers")
    parser.add_argument("--max-attempts", type=int, default=3,
                        help="Max attempts per turn")
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

    target_image = component_dir / args.target_image
    footprint_path = component_dir / args.footprint
    prompt_path = component_dir / args.prompt
    iteration_prompt_path = component_dir / args.iteration_prompt
    calibration_path = component_dir / args.calibration
    output_dir = component_dir / args.output_dir

    # Find core scripts directory (sibling to component directory's parent)
    script_dir = Path(__file__).parent.resolve()
    compare_script = script_dir / "compare_absolute.py"
    calibrate_script = script_dir / "calibrate_boundary.py"

    # Find catalogue
    if args.catalogue:
        catalogue_path = Path(args.catalogue).resolve()
    else:
        # Default: look in michaelangelo/reference/
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
    print("Multi-Turn Seed Exploration")
    print(f"Model: {args.model}")
    print(f"Component: {component_dir.name}")
    print(f"Base seed: {args.base_seed}, Range: +/-{args.seed_range}")
    print(f"Parallel workers: {args.num_parallel}")
    print("=" * 70)

    # Generate calibration if needed
    if not calibration_path.exists():
        print("\nGenerating calibration...")
        if not generate_calibration(component_dir, calibrate_script, target_image,
                                     footprint_path, calibration_path):
            print("ERROR: Failed to generate calibration")
            sys.exit(1)
        print(f"Calibration saved to: {calibration_path}")

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate seed list
    seeds = list(range(args.base_seed - args.seed_range, args.base_seed + args.seed_range + 1))
    print(f"\nWill test {len(seeds)} seeds: {seeds[0]} to {seeds[-1]}")

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

    # Run seeds in parallel
    results = []
    with ThreadPoolExecutor(max_workers=args.num_parallel) as executor:
        futures = {
            executor.submit(
                run_seed_multiturn,
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
                api_key=api_key,
                model=args.model,
                max_attempts=args.max_attempts
            ): seed
            for seed in seeds
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
                    "turn1_success": False,
                    "turn2_success": False,
                    "turn1_metrics": None,
                    "turn2_metrics": None
                })

    # Sort by seed
    results.sort(key=lambda x: x["seed"])

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

    # Calculate improvements and rankings
    ranked_results = []
    for r in results:
        if r["turn2_metrics"] and r["turn2_metrics"]["IoU"] is not None:
            entry = {
                "seed": r["seed"],
                "turn1": r["turn1_metrics"],
                "turn2": r["turn2_metrics"],
                "final_iou": r["turn2_metrics"]["IoU"],
                "final_dice": r["turn2_metrics"]["Dice"],
                "final_sse": r["turn2_metrics"].get("SSE", float('inf'))
            }

            # Calculate improvement if Turn 1 metrics exist
            if r["turn1_metrics"] and r["turn1_metrics"]["IoU"]:
                iou_change = (r["turn2_metrics"]["IoU"] - r["turn1_metrics"]["IoU"]) / r["turn1_metrics"]["IoU"] * 100
                dice_change = (r["turn2_metrics"]["Dice"] - r["turn1_metrics"]["Dice"]) / r["turn1_metrics"]["Dice"] * 100
                entry["improvement"] = {
                    "IoU": f"{'+' if iou_change > 0 else ''}{iou_change:.1f}%",
                    "Dice": f"{'+' if dice_change > 0 else ''}{dice_change:.1f}%"
                }
                # SSE improvement (negative is better - fewer errors)
                if r["turn1_metrics"].get("SSE") and r["turn1_metrics"]["SSE"] > 0:
                    sse_change = (r["turn2_metrics"].get("SSE", 0) - r["turn1_metrics"]["SSE"]) / r["turn1_metrics"]["SSE"] * 100
                    entry["improvement"]["SSE"] = f"{'+' if sse_change > 0 else ''}{sse_change:.1f}%"

            ranked_results.append(entry)

    # Rank by SSE (lower is better) - PRIMARY METRIC
    ranked_by_sse = sorted(ranked_results, key=lambda x: x["final_sse"], reverse=False)

    # Rank by IoU (higher is better) - kept for backward compatibility
    ranked_by_iou = sorted(ranked_results, key=lambda x: x["final_iou"], reverse=True)

    # Rank by Dice (higher is better)
    ranked_by_dice = sorted(ranked_results, key=lambda x: x["final_dice"], reverse=True)

    print("\n--- Top 5 by SSE (lower is better) ---")
    for i, r in enumerate(ranked_by_sse[:5], 1):
        sse_change = r.get("improvement", {}).get("SSE", "N/A")
        print(f"  {i}. Seed {r['seed']}: SSE={r['final_sse']:.0f} (change: {sse_change})")

    print("\n--- Top 5 by IoU (higher is better) ---")
    for i, r in enumerate(ranked_by_iou[:5], 1):
        improvement = r.get("improvement", {}).get("IoU", "N/A")
        print(f"  {i}. Seed {r['seed']}: IoU={r['final_iou']:.4f} (improvement: {improvement})")

    # Save exploration summary
    exploration_summary = {
        "model": args.model,
        "thinking_level": "high",
        "seeds_tested": len(seeds),
        "turn1_successful": len(turn1_successes),
        "turn2_successful": len(turn2_successes),
        "elapsed_time": str(elapsed),
        # SSE-based rankings (primary metric - lower is better)
        "best_seed_by_sse": ranked_by_sse[0]["seed"] if ranked_by_sse else None,
        "ranked_by_sse": ranked_by_sse[:10],
        # IoU-based rankings (backward compatibility - higher is better)
        "best_seed_by_iou": ranked_by_iou[0]["seed"] if ranked_by_iou else None,
        "best_seed_by_dice": ranked_by_dice[0]["seed"] if ranked_by_dice else None,
        "ranked_by_iou": ranked_by_iou[:10],
        "ranked_by_dice": ranked_by_dice[:10],
        "all_results": results
    }

    summary_path = output_dir / "exploration_summary.json"
    with open(summary_path, "w") as f:
        json.dump(exploration_summary, f, indent=2)

    print(f"\nExploration summary saved to: {summary_path}")
    print("=" * 70)

    return len(turn2_successes) > 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
