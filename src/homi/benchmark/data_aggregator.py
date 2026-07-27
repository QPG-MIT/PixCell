"""Data aggregation module for collecting benchmark results across all papers and models."""

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pandas as pd


@dataclass
class BenchmarkResult:
    """Unified benchmark result schema."""
    paper_id: str
    model_key: str
    model_name: str
    model_family: str
    model_version: float
    model_version_name: str

    # Performance metrics
    best_iou: float
    mean_iou: float
    best_sse: float
    mean_sse: float
    best_dice: float

    # Success rates
    turn1_success_rate: float
    turn2_success_rate: float
    phase1_runs: int
    phase2_runs: int

    # Efficiency (optional)
    total_tokens: Optional[int] = None
    total_duration_seconds: Optional[float] = None


def get_model_family(model_key: str) -> str:
    """Extract model family from model key."""
    model_lower = model_key.lower()

    if 'gemini' in model_lower:
        return 'gemini'
    elif 'claude' in model_lower or 'anthropic' in model_lower:
        return 'claude'
    elif 'gpt' in model_lower or 'openai' in model_lower:
        return 'openai'
    elif 'grok' in model_lower:
        return 'grok'
    elif 'qwen' in model_lower:
        return 'qwen'
    else:
        return 'other'


def get_model_version(model_key: str) -> tuple[float, str]:
    """Extract numeric version and version name from model key.

    Returns:
        (numeric_version, version_name) tuple
    """
    model_lower = model_key.lower()

    # Gemini versions (check 3.1 before 3.0 to avoid substring match)
    if 'gemini-3.1-pro' in model_lower or 'gemini-3-1-pro' in model_lower:
        return 3.11, '3.1-pro'
    elif 'gemini-3.1-flash' in model_lower or 'gemini-3-1-flash' in model_lower:
        return 3.1, '3.1-flash-lite'
    elif 'gemini-3-pro' in model_lower:
        return 3.01, '3.0-pro'
    elif 'gemini-3-flash' in model_lower:
        return 3.0, '3.0-flash'
    elif 'gemini-2.5-pro' in model_lower:
        return 2.51, '2.5-pro'
    elif 'gemini-2.5-flash' in model_lower:
        return 2.5, '2.5-flash'
    elif 'gemini-2.0' in model_lower or 'gemini-2-0' in model_lower:
        return 2.0, '2.0-flash'

    # Claude versions
    elif 'opus-4.5' in model_lower or 'opus-4-5' in model_lower:
        return 4.5, 'opus-4.5'
    elif 'sonnet-4.5' in model_lower or 'sonnet-4-5' in model_lower:
        return 4.5, 'sonnet-4.5'

    # OpenAI versions
    elif 'gpt-5.2' in model_lower or 'gpt-5-2' in model_lower:
        return 5.2, 'gpt-5.2'
    elif 'gpt-5' in model_lower:
        return 5.0, 'gpt-5'

    # Others
    elif 'grok-4' in model_lower:
        return 4.0, 'grok-4'
    elif 'qwen3' in model_lower and 'thinking' in model_lower:
        return 3.0, 'qwen3-thinking'
    elif 'qwen3' in model_lower and 'instruct' in model_lower:
        return 3.0, 'qwen3-instruct'

    return 0.0, 'unknown'


def get_display_name(model_key: str) -> str:
    """Get human-readable model name."""
    family = get_model_family(model_key)
    _, version_name = get_model_version(model_key)

    name_map = {
        ('gemini', '3.1-pro'): 'Gemini 3.1 Pro',
        ('gemini', '3.1-flash-lite'): 'Gemini 3.1 Flash Lite',
        ('gemini', '3.0-pro'): 'Gemini 3.0 Pro',
        ('gemini', '3.0-flash'): 'Gemini 3.0 Flash',
        ('gemini', '2.5-pro'): 'Gemini 2.5 Pro',
        ('gemini', '2.5-flash'): 'Gemini 2.5 Flash',
        ('gemini', '2.0-flash'): 'Gemini 2.0 Flash',
        ('claude', 'opus-4.5'): 'Claude Opus 4.5',
        ('claude', 'sonnet-4.5'): 'Claude Sonnet 4.5',
        ('openai', 'gpt-5.2'): 'GPT-5.2',
        ('openai', 'gpt-5'): 'GPT-5',
        ('grok', 'grok-4'): 'Grok 4',
        ('qwen', 'qwen3-thinking'): 'Qwen3-VL Thinking',
        ('qwen', 'qwen3-instruct'): 'Qwen3-VL Instruct',
    }

    return name_map.get((family, version_name), model_key)


def parse_exploration_summary(summary_path: Path) -> dict:
    """Parse an exploration_summary.json file."""
    with open(summary_path) as f:
        data = json.load(f)

    # Extract best metrics from ranked results
    ranked_by_iou = data.get('ranked_by_iou', [])
    ranked_by_sse = data.get('ranked_by_sse', [])

    best_iou = ranked_by_iou[0].get('final_iou', 0) if ranked_by_iou else 0
    mean_iou = sum(r.get('final_iou', 0) for r in ranked_by_iou) / len(ranked_by_iou) if ranked_by_iou else 0

    best_sse = ranked_by_sse[0].get('final_sse', float('inf')) if ranked_by_sse else float('inf')
    mean_sse = sum(r.get('final_sse', float('inf')) for r in ranked_by_sse) / len(ranked_by_sse) if ranked_by_sse else float('inf')

    best_dice = ranked_by_iou[0].get('final_dice', 0) if ranked_by_iou else 0

    # Success rates
    total_runs = data.get('runs_total', 0)
    turn1_success = data.get('turn1_successful', 0)
    turn2_success = data.get('turn2_successful', 0)

    turn1_rate = turn1_success / total_runs if total_runs > 0 else 0
    turn2_rate = turn2_success / total_runs if total_runs > 0 else 0

    return {
        'best_iou': best_iou,
        'mean_iou': mean_iou,
        'best_sse': best_sse,
        'mean_sse': mean_sse,
        'best_dice': best_dice,
        'turn1_success_rate': turn1_rate,
        'turn2_success_rate': turn2_rate,
        'phase1_runs': total_runs,
    }


def parse_extended_summary(summary_path: Path) -> dict:
    """Parse an extended_exploration_summary.json file (Phase 2)."""
    with open(summary_path) as f:
        data = json.load(f)

    ranked_by_iou = data.get('ranked_by_iou', [])

    best_iou = ranked_by_iou[0].get('final_iou', 0) if ranked_by_iou else 0
    best_sse = ranked_by_iou[0].get('final_sse', float('inf')) if ranked_by_iou else float('inf')

    return {
        'phase2_best_iou': best_iou,
        'phase2_best_sse': best_sse,
        'phase2_runs': data.get('runs_completed', 0),
    }


def extract_model_key_from_path(benchmark_dir: Path) -> str:
    """Extract model key from benchmark directory name.

    Example: benchmark_gemini_gemini-3-flash-preview -> gemini/gemini-3-flash-preview
    """
    dirname = benchmark_dir.name

    # Pattern: benchmark_{provider}_{model-name}
    match = re.match(r'benchmark_(\w+)_(.+)', dirname)
    if match:
        provider = match.group(1)
        model_name = match.group(2)
        return f"{provider}/{model_name}"

    return dirname


def aggregate_benchmark_data(base_path: str) -> pd.DataFrame:
    """Aggregate all benchmark data from FINAL_1-8 into a unified DataFrame.

    Args:
        base_path: Path to gemini_images_run directory

    Returns:
        DataFrame with benchmark results for all papers and models
    """
    base = Path(base_path)
    results = []

    # Find all FINAL_* directories
    paper_dirs = sorted(base.glob("FINAL_*"))

    for paper_dir in paper_dirs:
        paper_id = paper_dir.name

        # Find all benchmark directories
        benchmark_dirs = list(paper_dir.glob("benchmark_*"))

        for benchmark_dir in benchmark_dirs:
            if not benchmark_dir.is_dir():
                continue

            model_key = extract_model_key_from_path(benchmark_dir)
            model_family = get_model_family(model_key)
            model_version, version_name = get_model_version(model_key)
            model_name = get_display_name(model_key)

            # Try to find exploration summary (Phase 1)
            summary_paths = list(benchmark_dir.glob("**/exploration_summary.json"))

            metrics = {
                'best_iou': 0,
                'mean_iou': 0,
                'best_sse': float('inf'),
                'mean_sse': float('inf'),
                'best_dice': 0,
                'turn1_success_rate': 0,
                'turn2_success_rate': 0,
                'phase1_runs': 0,
            }

            if summary_paths:
                try:
                    metrics = parse_exploration_summary(summary_paths[0])
                except Exception as e:
                    print(f"Warning: Could not parse {summary_paths[0]}: {e}")

            # Try to find extended summary (Phase 2)
            extended_paths = list(benchmark_dir.glob("**/extended_exploration_summary.json"))
            phase2_metrics = {'phase2_runs': 0, 'phase2_best_iou': 0, 'phase2_best_sse': float('inf')}

            if extended_paths:
                try:
                    phase2_metrics = parse_extended_summary(extended_paths[0])
                except Exception as e:
                    print(f"Warning: Could not parse {extended_paths[0]}: {e}")

            # Use best of Phase 1 or Phase 2
            final_iou = max(metrics['best_iou'], phase2_metrics.get('phase2_best_iou', 0))
            final_sse = min(metrics['best_sse'], phase2_metrics.get('phase2_best_sse', float('inf')))

            results.append({
                'paper_id': paper_id,
                'model_key': model_key,
                'model_name': model_name,
                'model_family': model_family,
                'model_version': model_version,
                'model_version_name': version_name,
                'best_iou': final_iou,
                'mean_iou': metrics['mean_iou'],
                'best_sse': final_sse if final_sse != float('inf') else None,
                'mean_sse': metrics['mean_sse'] if metrics['mean_sse'] != float('inf') else None,
                'best_dice': metrics['best_dice'],
                'turn1_success_rate': metrics['turn1_success_rate'],
                'turn2_success_rate': metrics['turn2_success_rate'],
                'phase1_runs': metrics['phase1_runs'],
                'phase2_runs': phase2_metrics['phase2_runs'],
            })

    df = pd.DataFrame(results)

    # Sort by paper and model
    df = df.sort_values(['paper_id', 'model_family', 'model_version'])

    return df


def load_telemetry_data(base_path: str) -> pd.DataFrame:
    """Load telemetry summary data for token usage analysis."""
    base = Path(base_path)
    results = []

    telemetry_files = base.glob("**/telemetry_summary.json")

    for telemetry_path in telemetry_files:
        try:
            with open(telemetry_path) as f:
                data = json.load(f)

            # Extract paper_id and model from path
            parts = telemetry_path.parts
            paper_id = None
            for part in parts:
                if part.startswith('FINAL_'):
                    paper_id = part
                    break

            if paper_id:
                results.append({
                    'paper_id': paper_id,
                    'model': data.get('model', ''),
                    'runs_total': data.get('runs_total', 0),
                    'runs_successful': data.get('runs_successful', 0),
                    'total_input_tokens': data.get('aggregate_usage', {}).get('total_input_tokens', 0),
                    'total_output_tokens': data.get('aggregate_usage', {}).get('total_output_tokens', 0),
                })
        except Exception as e:
            print(f"Warning: Could not parse {telemetry_path}: {e}")

    return pd.DataFrame(results)


if __name__ == "__main__":
    # Test aggregation
    from homi.paths import projects_dir

    df = aggregate_benchmark_data(str(projects_dir() / "gemini_images_run"))
    print(f"Aggregated {len(df)} benchmark results")
    print(df.head(20))
    print("\nModel families found:", df['model_family'].unique())
    print("Papers found:", df['paper_id'].unique())
