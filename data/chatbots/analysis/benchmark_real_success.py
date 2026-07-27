#!/usr/bin/env python3
"""
HOMI Benchmark: Real Success Rate Analysis

Key insight: Scripts without GDSFactory primitives are FAILURES regardless of IoU,
because they cannot be used in the sweep/simulate pipeline.

Metrics:
1. Primitive Success Rate - % of runs producing usable parametric scripts
2. Quality When Usable - avg IoU for primitive-based scripts only
3. Expected Usable IoU - primitive_rate × avg_IoU_primitives (combined metric)

Categories:
- SUCCESS: Uses primitives + IoU >= 0.5 (ready for simulation)
- PARTIAL: Uses primitives + IoU < 0.5 (needs JEE optimization)
- FAILURE: No primitives (unusable regardless of IoU)
"""

import re
import json
from pathlib import Path
from collections import defaultdict
import statistics

# === PATTERNS ===

PHOTONIC_PRIMITIVES = [
    r'gf\.components\.straight\b',
    r'gf\.components\.bend_euler\b',
    r'gf\.components\.bend_circular\b',
    r'gf\.components\.bend_s\b',
    r'gf\.components\.taper\b',
    r'gf\.components\.taper_cross_section\b',
    r'gf\.components\.mmi\d*x\d*\b',
    r'gf\.components\.mmi\b',
    r'gf\.components\.coupler\b',
    r'gf\.components\.coupler_ring\b',
    r'gf\.components\.coupler_straight\b',
    r'gf\.components\.ring\b',
    r'gf\.components\.ring_single\b',
    r'gf\.components\.ring_double\b',
    r'gf\.components\.spiral\b',
    r'gf\.components\.splitter\b',
    r'gf\.components\.y_branch\b',
    r'gf\.components\.directional_coupler\b',
    r'gf\.components\.grating_coupler\b',
    r'gf\.routing\.',
]

MODEL_NAMES = {
    'x-ai_grok-4': 'Grok-4',
    'qwen_qwen3-vl-235b-a22b-instruct': 'Qwen-VL-Instruct',
    'qwen_qwen3-vl-235b-a22b-thinking': 'Qwen-VL-Thinking',
    'gemini_gemini-3-pro-preview': 'Gemini-3-Pro',
    'gemini-3-pro-preview': 'Gemini-3-Pro',
    'gemini_gemini-3-flash-preview': 'Gemini-3-Flash',
    'gemini_gemini-2.5-pro': 'Gemini-2.5-Pro',
    'gemini_gemini-2.5-flash': 'Gemini-2.5-Flash',
    'gemini_gemini-2.0-flash': 'Gemini-2.0-Flash',
    'anthropic_claude-opus-4.5': 'Claude-Opus-4.5',
    'anthropic_claude-sonnet-4.5': 'Claude-Sonnet-4.5',
}

IOU_THRESHOLD = 0.5  # Above this = ready to use, below = needs JEE


def uses_primitives(content: str) -> bool:
    """Check if script uses GDSFactory photonic primitives."""
    for pattern in PHOTONIC_PRIMITIVES:
        if re.search(pattern, content):
            return True
    return False


def get_model(path: str) -> str:
    # Match both phase1/phase2 and multiturn_seeds patterns
    match = re.search(r'benchmark_([^/]+)/(phase|multiturn)', path)
    if match:
        raw = match.group(1)
        return MODEL_NAMES.get(raw, raw)
    return None


def get_project(path: str) -> str:
    match = re.search(r'(FINAL_\d+)', path)
    return match.group(1) if match else None


def load_metrics(script_path: Path) -> dict:
    metrics_path = script_path.parent / "metrics.json"
    if metrics_path.exists():
        try:
            with open(metrics_path) as f:
                return json.load(f)
        except:
            pass
    return {}


def main():
    import sys

    base_path = Path(__file__).resolve().parents[1] / "trajectories"
    scripts = list(base_path.glob("**/generated_component.py"))

    # The audited cohort is part of the record: by default, regenerate over
    # exactly the models the shipped aggregates contain (the trajectories
    # also hold runs of models that postdate the audit; include them only
    # with --all).
    cohort = None
    json_record = Path(__file__).resolve().parents[1] / "aggregates/real_success_data.json"
    if "--all" not in sys.argv and json_record.exists():
        cohort = {row["model"] for row in json.loads(json_record.read_text())}

    # Collect data
    model_data = defaultdict(lambda: {
        'success': [],      # primitives + IoU >= 0.5
        'partial': [],      # primitives + IoU < 0.5
        'failure': [],      # no primitives
        'all_primitive_iou': [],
        'all_failure_iou': [],
    })

    for script_path in scripts:
        try:
            content = script_path.read_text()
        except:
            continue

        model = get_model(str(script_path))
        if not model or model == 'unknown' or 'openai' in str(script_path).lower():
            continue
        if cohort is not None and model not in cohort:
            continue

        metrics = load_metrics(script_path)
        iou = metrics.get('IoU')
        sse = metrics.get('SSE')
        has_primitives = uses_primitives(content)

        entry = {'iou': iou, 'sse': sse, 'path': str(script_path)}

        if has_primitives:
            if iou is not None:
                model_data[model]['all_primitive_iou'].append(iou)
            if iou is not None and iou >= IOU_THRESHOLD:
                model_data[model]['success'].append(entry)
            else:
                model_data[model]['partial'].append(entry)
        else:
            model_data[model]['failure'].append(entry)
            if iou is not None:
                model_data[model]['all_failure_iou'].append(iou)

    # Calculate metrics
    results = []
    for model, data in model_data.items():
        total = len(data['success']) + len(data['partial']) + len(data['failure'])
        if total < 10:
            continue

        n_success = len(data['success'])
        n_partial = len(data['partial'])
        n_failure = len(data['failure'])
        n_usable = n_success + n_partial

        primitive_rate = n_usable / total
        success_rate = n_success / total

        avg_iou_primitives = statistics.mean(data['all_primitive_iou']) if data['all_primitive_iou'] else 0
        avg_iou_failures = statistics.mean(data['all_failure_iou']) if data['all_failure_iou'] else 0

        # Expected usable IoU = primitive_rate * avg_iou_primitives
        expected_usable_iou = primitive_rate * avg_iou_primitives

        results.append({
            'model': model,
            'total': total,
            'success': n_success,
            'partial': n_partial,
            'failure': n_failure,
            'primitive_rate': primitive_rate,
            'success_rate': success_rate,
            'avg_iou_primitives': avg_iou_primitives,
            'avg_iou_failures': avg_iou_failures,
            'expected_usable_iou': expected_usable_iou,
        })

    # Sort by expected usable IoU (the combined metric)
    results.sort(key=lambda x: x['expected_usable_iou'], reverse=True)

    # === GENERATE REPORT ===

    report = []
    report.append("# HOMI Benchmark: Real Success Rate Analysis")
    report.append("")
    report.append("## The Problem with Raw IoU/SSE")
    report.append("")
    report.append("A model can achieve high IoU using raw polygon vertices, but this output is **unusable**:")
    report.append("- Cannot sweep parameters (no `length`, `gap`, `radius` to tune)")
    report.append("- Cannot simulate in Tidy3D (no proper cross-sections)")
    report.append("- Cannot use Weber explorer (no parameters to generate sliders)")
    report.append("- Cannot use JEE optimizer (nothing to optimize)")
    report.append("")
    report.append("**Therefore: Non-primitive outputs = FAILURES regardless of IoU score.**")
    report.append("")
    report.append("## Metrics")
    report.append("")
    report.append("| Metric | Description |")
    report.append("|--------|-------------|")
    report.append("| **Primitive Rate** | % of runs producing usable parametric scripts |")
    report.append("| **Success Rate** | % of runs with primitives AND IoU ≥ 0.5 |")
    report.append("| **Avg IoU (Usable)** | Mean IoU for primitive-based scripts only |")
    report.append("| **Expected Usable IoU** | `primitive_rate × avg_IoU` - combined quality metric |")
    report.append("")
    report.append("## Categories")
    report.append("")
    report.append("- **SUCCESS** (green): Uses primitives + IoU ≥ 0.5 → Ready for simulation")
    report.append("- **PARTIAL** (yellow): Uses primitives + IoU < 0.5 → Needs JEE optimization")
    report.append("- **FAILURE** (red): No primitives → Unusable, pipeline dead-end")
    report.append("")

    # Main results table
    report.append("## Results by Model")
    report.append("")
    report.append("*Sorted by Expected Usable IoU (the metric that matters)*")
    report.append("")
    report.append("| Rank | Model | Total | Success | Partial | Failure | Prim % | Exp. IoU |")
    report.append("|-----:|-------|------:|--------:|--------:|--------:|-------:|---------:|")

    for i, r in enumerate(results, 1):
        report.append(
            f"| {i} | **{r['model']}** | {r['total']} | "
            f"{r['success']} | {r['partial']} | {r['failure']} | "
            f"{r['primitive_rate']*100:.1f}% | **{r['expected_usable_iou']:.3f}** |"
        )

    report.append("")
    report.append("## Detailed Breakdown")
    report.append("")
    report.append("| Model | Prim Rate | Avg IoU (Prim) | Avg IoU (Fail) | Delta |")
    report.append("|-------|----------:|---------------:|---------------:|------:|")

    for r in results:
        delta = r['avg_iou_primitives'] - r['avg_iou_failures'] if r['avg_iou_failures'] > 0 else 0
        report.append(
            f"| {r['model']} | {r['primitive_rate']*100:.1f}% | "
            f"{r['avg_iou_primitives']:.3f} | {r['avg_iou_failures']:.3f} | "
            f"{delta:+.3f} |"
        )

    report.append("")
    report.append("## Stacked Bar Data (for visualization)")
    report.append("")
    report.append("```")
    report.append("Model                  | Success | Partial | Failure | Total")
    report.append("-----------------------|---------|---------|---------|------")
    for r in results:
        s_pct = r['success'] / r['total'] * 100
        p_pct = r['partial'] / r['total'] * 100
        f_pct = r['failure'] / r['total'] * 100
        bar_s = '█' * int(s_pct / 5)
        bar_p = '▓' * int(p_pct / 5)
        bar_f = '░' * int(f_pct / 5)
        report.append(f"{r['model']:<22} | {s_pct:5.1f}%  | {p_pct:5.1f}%  | {f_pct:5.1f}%  | {bar_s}{bar_p}{bar_f}")
    report.append("```")
    report.append("")
    report.append("Legend: █ Success (ready) | ▓ Partial (needs JEE) | ░ Failure (unusable)")

    report.append("")
    report.append("## Key Findings")
    report.append("")

    # Find best and worst
    best = results[0]
    worst = results[-1]

    report.append(f"1. **{best['model']}** leads with {best['primitive_rate']*100:.1f}% usable outputs and Expected IoU of {best['expected_usable_iou']:.3f}")
    report.append(f"2. **{worst['model']}** has only {worst['primitive_rate']*100:.1f}% usable outputs - {worst['failure']} of {worst['total']} runs are failures")
    report.append("")

    # Find models where failure IoU > primitive IoU (the misleading case)
    misleading = [r for r in results if r['avg_iou_failures'] > r['avg_iou_primitives'] and r['avg_iou_failures'] > 0]
    if misleading:
        report.append("### The Misleading IoU Problem")
        report.append("")
        report.append("These models achieve HIGHER IoU when using polygons (failures) than primitives:")
        report.append("")
        for r in misleading:
            report.append(f"- **{r['model']}**: Failure IoU ({r['avg_iou_failures']:.3f}) > Primitive IoU ({r['avg_iou_primitives']:.3f})")
        report.append("")
        report.append("This shows why raw IoU is a misleading metric - the 'better' scores are unusable!")

    # Grok-4 vs Qwen comparison
    report.append("")
    report.append("## Grok-4 vs Qwen-VL-Instruct")
    report.append("")
    grok = next((r for r in results if r['model'] == 'Grok-4'), None)
    qwen = next((r for r in results if r['model'] == 'Qwen-VL-Instruct'), None)

    if grok and qwen:
        report.append("| Metric | Grok-4 | Qwen-VL-Instruct |")
        report.append("|--------|-------:|-----------------:|")
        report.append(f"| Primitive Rate | {grok['primitive_rate']*100:.1f}% | {qwen['primitive_rate']*100:.1f}% |")
        report.append(f"| Success Rate | {grok['success_rate']*100:.1f}% | {qwen['success_rate']*100:.1f}% |")
        report.append(f"| Avg IoU (Usable) | {grok['avg_iou_primitives']:.3f} | {qwen['avg_iou_primitives']:.3f} |")
        report.append(f"| Expected Usable IoU | **{grok['expected_usable_iou']:.3f}** | **{qwen['expected_usable_iou']:.3f}** |")
        report.append(f"| Failure Count | {grok['failure']}/{grok['total']} | {qwen['failure']}/{qwen['total']} |")

    # Write report
    output_path = Path(__file__).resolve().parents[1] / "aggregates/real_success_benchmark.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        f.write('\n'.join(report))

    # Write JSON for programmatic use
    json_path = Path(__file__).resolve().parents[1] / "aggregates/real_success_data.json"
    with open(json_path, 'w') as f:
        json.dump(results, f, indent=2)

    # Print report
    print('\n'.join(report))
    print(f"\n\nReport saved to: {output_path}")
    print(f"JSON data saved to: {json_path}")


if __name__ == "__main__":
    main()
