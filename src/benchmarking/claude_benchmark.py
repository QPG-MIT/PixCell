#!/usr/bin/env python3
"""
Claude-only benchmark for HOMI GDS generation.

Benchmarks Claude Opus 4.5 and Sonnet 4.5 with conservative parallelism, optimized for
Anthropic API rate limits. All models run with extended thinking at highest config.

Models (Massive Run Selection):
  - Claude Opus 4.5 (claude-opus-4.5) - latest flagship
  - Claude Sonnet 4.5 (claude-sonnet-4.5) - latest balanced

Usage:
    python -m benchmarking.claude_benchmark --papers 1x2_coupler 2_004629
    python -m benchmarking.claude_benchmark --papers paper1 paper2 paper3 paper4
    python -m benchmarking.claude_benchmark --dry-run --papers 1x2_coupler
"""

import argparse
import shutil
from pathlib import Path
from typing import List

from homi.paths import michaelangelo_dir, projects_dir

from benchmarking.config import (
    BenchmarkConfig,
    BenchmarkModel,
    Phase1Config,
    Phase2Config,
)
from benchmarking.runner import BenchmarkRunner
from benchmarking.aggregator import ResultsAggregator
from benchmarking.reporter import ReportGenerator


# =============================================================================
# CLAUDE MODELS - 5 models from the Anthropic Claude family
# =============================================================================
# Claude model characteristics:
#   - No deterministic seeds (supports_seed=False)
#   - Extended thinking on all 4.x and 3.7 models
#   - Vision/multimodal input supported
#   - Conservative rate limits (tier-dependent)
#   - All models run with thinking enabled at highest config
# =============================================================================

CLAUDE_MODELS: List[BenchmarkModel] = [
    # Selected for massive benchmark run: Opus 4.5 and Sonnet 4.5
    BenchmarkModel(
        name="Claude Opus 4.5",
        model_key="anthropic/claude-opus-4.5",
        family="claude",
        supports_seed=False,
        supports_thinking=True,
    ),
    BenchmarkModel(
        name="Claude Sonnet 4.5",
        model_key="anthropic/claude-sonnet-4.5",
        family="claude",
        supports_seed=False,
        supports_thinking=True,
    ),
]


def create_claude_config(
    papers: List[str],
    num_seeds: int = 15,
    base_seed: int = 1333,
    phase1_parallel: int = 8,
    phase2_top_k: int = 3,
    phase2_parallel: int = 3,
    phase2_turns: int = 3,
    output_dir: Path = Path("benchmark_results"),
    projects_dir: Path = projects_dir(),
    michaelangelo_dir: Path = michaelangelo_dir(),
) -> BenchmarkConfig:
    """Create benchmark config optimized for Claude models.

    Default settings respect Anthropic's conservative rate limits:
    - Phase 1: 4 parallel seeds (vs Gemini's 15)
    - Phase 2: 2 parallel seeds (vs Gemini's 5)
    - Model parallelism: 2 concurrent paper/model combos

    Note: Claude does not support deterministic seeds, so different runs
    with the same base_seed may produce varying results. This is accounted
    for in the benchmark by running multiple seeds/runs regardless.
    """
    # Conservative max parallel: 2 paper/model combos at a time
    max_parallel = min(len(papers) * len(CLAUDE_MODELS), 2)

    return BenchmarkConfig(
        papers=papers,
        models=CLAUDE_MODELS.copy(),
        phase1=Phase1Config(
            num_seeds=num_seeds,
            base_seed=base_seed,
            num_parallel=phase1_parallel,
            max_attempts=3,
        ),
        phase2=Phase2Config(
            top_k=phase2_top_k,
            num_parallel=phase2_parallel,
            additional_turns=phase2_turns,
            max_attempts=3,
        ),
        num_parallel_models=max_parallel,
        output_dir=output_dir,
        projects_dir=projects_dir,
        michaelangelo_dir=michaelangelo_dir,
    )


def clean_phase_directories(
    papers: List[str],
    models: List[BenchmarkModel],
    clean_models: List[str],
    projects_dir: Path,
) -> None:
    """Clean phase1/phase2 directories for specified models.

    Args:
        papers: List of paper names
        models: List of BenchmarkModel objects
        clean_models: List of model keys to clean (e.g., 'claude-opus-4-5') or ['all']
        projects_dir: Path to projects directory
    """
    clean_all = "all" in clean_models

    for paper in papers:
        for model in models:
            # Extract model ID from key (e.g., "anthropic/claude-opus-4-5-20251101" -> "claude-opus-4-5-20251101")
            model_id = model.model_key.split("/")[-1]

            # Check if this model should be cleaned
            if not clean_all:
                should_clean = any(
                    m in model_id or model_id in m for m in clean_models
                )
                if not should_clean:
                    continue

            # Construct component dir name (same format as runner uses)
            provider = model.model_key.split("/")[0]
            component_dir_name = f"benchmark_{provider}_{model_id}"
            component_dir = projects_dir / paper / component_dir_name

            if not component_dir.exists():
                continue

            # Clean phase1 and phase2 directories
            for phase_dir in ["phase1", "phase2"]:
                phase_path = component_dir / phase_dir
                if phase_path.exists():
                    print(f"  Cleaning {phase_path}")
                    shutil.rmtree(phase_path)

    print("  Clean complete.\n")


def main():
    parser = argparse.ArgumentParser(
        description="Run Claude-only GDS generation benchmark",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Claude Models Benchmarked (Massive Run Selection - all with extended thinking):
  - Claude Opus 4.5 (claude-opus-4.5) - latest flagship
  - Claude Sonnet 4.5 (claude-sonnet-4.5) - latest balanced

Note: Claude models do NOT support deterministic seeds. Multiple runs may
produce varying results even with the same configuration. The benchmark
accounts for this by testing multiple independent runs.

Examples:
  # Run on default papers
  python -m benchmarking.claude_benchmark

  # Run on specific papers
  python -m benchmarking.claude_benchmark --papers paper1 paper2 paper3 paper4

  # Custom Phase 1 settings (conservative for rate limits)
  python -m benchmarking.claude_benchmark --phase1-seeds 10 --phase1-parallel 2

  # Dry run to validate configuration
  python -m benchmarking.claude_benchmark --dry-run --papers 1x2_coupler

  # Aggregate existing results only
  python -m benchmarking.claude_benchmark --aggregate benchmark_results/2026-01-23_120000
        """
    )

    # Aggregate mode
    parser.add_argument(
        "--aggregate",
        type=Path,
        default=None,
        help="Only aggregate results from existing benchmark directory"
    )

    # Papers
    parser.add_argument(
        "--papers",
        nargs="+",
        default=["1x2_coupler", "2_004629"],
        help="Papers to benchmark (project directory names)"
    )

    # Model filter
    parser.add_argument(
        "--models",
        nargs="+",
        default=None,
        metavar="MODEL",
        help="Only run specific models (e.g., 'claude-opus-4-5 claude-sonnet-4'). "
             "Use model IDs without 'anthropic/' prefix. Default: run all 2 models."
    )

    # Phase 1 config
    parser.add_argument(
        "--phase1-seeds",
        type=int,
        default=15,
        help="Number of seeds/runs for Phase 1 (default: 15)"
    )
    parser.add_argument(
        "--phase1-parallel",
        type=int,
        default=8,
        help="Parallel workers for Phase 1 seeds (default: 8)"
    )
    parser.add_argument(
        "--phase1-base-seed",
        type=int,
        default=1333,
        help="Base seed for Phase 1 (default: 1333). Note: Claude ignores seeds."
    )

    # Phase 2 config
    parser.add_argument(
        "--phase2-top",
        type=int,
        default=3,
        help="Number of top seeds by SSE for Phase 2 (default: 3)"
    )
    parser.add_argument(
        "--phase2-parallel",
        type=int,
        default=3,
        help="Parallel workers for Phase 2 seeds (default: 3)"
    )
    parser.add_argument(
        "--phase2-turns",
        type=int,
        default=3,
        help="Additional turns in Phase 2 (default: 3)"
    )

    # Directories
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("benchmark_results"),
        help="Output directory for results (default: benchmark_results)"
    )
    parser.add_argument(
        "--projects-dir",
        type=Path,
        default=projects_dir(),
        help="Projects directory (default: projects)"
    )
    parser.add_argument(
        "--michaelangelo-dir",
        type=Path,
        default=michaelangelo_dir(),
        help="Michaelangelo directory (default: michaelangelo)"
    )

    # Dry run
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only validate configuration, don't run benchmark"
    )

    # Clean option to clear stale results
    parser.add_argument(
        "--clean",
        nargs="*",
        default=None,
        metavar="MODEL",
        help="Clear phase1/phase2 dirs for specified models (or all if no args). "
             "Use model keys like 'claude-opus-4-5' or 'all' for all models."
    )

    args = parser.parse_args()

    # Aggregate-only mode
    if args.aggregate:
        print(f"Aggregating results from: {args.aggregate}")
        aggregate_results(args.aggregate)
        return

    # Create config
    config = create_claude_config(
        papers=args.papers,
        num_seeds=args.phase1_seeds,
        base_seed=args.phase1_base_seed,
        phase1_parallel=args.phase1_parallel,
        phase2_top_k=args.phase2_top,
        phase2_parallel=args.phase2_parallel,
        phase2_turns=args.phase2_turns,
        output_dir=args.output_dir,
        projects_dir=args.projects_dir,
        michaelangelo_dir=args.michaelangelo_dir,
    )

    # Filter models if --models specified
    if args.models:
        filtered_models = []
        for model in config.models:
            model_id = model.model_key.split("/")[-1]
            if any(m in model_id or model_id in m for m in args.models):
                filtered_models.append(model)
        if not filtered_models:
            print(f"ERROR: No models matched filter: {args.models}")
            print("Available models:")
            for m in config.models:
                print(f"  - {m.model_key.split('/')[-1]}")
            return
        config.models = filtered_models
        config.num_parallel_models = min(len(args.papers) * len(filtered_models), 2)

    # Print configuration
    print("=" * 70)
    print("HOMI Claude-Only Benchmark")
    print("=" * 70)
    print(f"Papers: {config.papers}")
    print(f"Models ({len(config.models)}):")
    for m in config.models:
        thinking = "extended thinking" if m.supports_thinking else "no thinking"
        print(f"  - {m.name} ({m.model_key}) [{thinking}]")
    print(f"Parallel (paper x model) combinations: {config.num_parallel_models}")
    print(f"Phase 1: {config.phase1.num_seeds} runs, {config.phase1.num_parallel} parallel")
    print(f"Phase 2: top {config.phase2.top_k}, {config.phase2.additional_turns} turns, "
          f"{config.phase2.num_parallel} parallel")
    print(f"Output: {config.output_dir}")
    print("=" * 70)

    # Important note about seeds
    print("\nNote: Claude models do NOT support deterministic seeds.")
    print("      Results may vary between runs even with identical config.")
    print("=" * 70)

    # Estimate
    total_phase1 = len(config.papers) * len(config.models) * config.phase1.num_seeds
    total_phase2 = len(config.papers) * len(config.models) * config.phase2.top_k
    print("\nEstimated API calls:")
    print(f"  Phase 1: {total_phase1} requests (max concurrent: {config.phase1.num_parallel})")
    print(f"  Phase 2: {total_phase2} requests (max concurrent: {config.phase2.num_parallel})")
    print("=" * 70)

    if args.dry_run:
        print("\nDry run - validating configuration...")
        runner = BenchmarkRunner(config)
        for paper in config.papers:
            try:
                runner._validate_paper(paper)
                print(f"  [OK] {paper}")
            except Exception as e:
                print(f"  [FAIL] {paper}: {e}")
        print("\nDry run complete.")
        return

    # Clean stale results if requested
    if args.clean is not None:
        clean_models = args.clean if args.clean else ["all"]
        print("\nCleaning stale results...")
        clean_phase_directories(
            papers=config.papers,
            models=config.models,
            clean_models=clean_models,
            projects_dir=config.projects_dir,
        )

    # Run benchmark
    print("\nStarting Claude benchmark...\n")
    runner = BenchmarkRunner(config)
    runner.run()

    # Generate reports
    print("\nGenerating reports...")
    aggregate_results(runner.run_dir)

    print(f"\nBenchmark complete! Results saved to: {runner.run_dir}")


def aggregate_results(benchmark_dir: Path):
    """Aggregate results and generate reports."""
    aggregator = ResultsAggregator(benchmark_dir)
    report = aggregator.aggregate()

    reporter = ReportGenerator(report, aggregator)
    reporter.generate_all(benchmark_dir)

    print("  [OK] comparison_report.json")
    print("  [OK] comparison_report.md")

    # Print summary
    print("\n" + "=" * 70)
    print("CLAUDE BENCHMARK RESULTS")
    print("=" * 70)
    print(f"Best by SSE: {report.overall_best_by_sse or 'N/A'}")
    print(f"Best by IoU: {report.overall_best_by_iou or 'N/A'}")

    for paper in report.papers:
        print(f"\n{paper}:")
        rankings = report.sse_rankings.get(paper, [])
        for rank, model in enumerate(rankings[:5], 1):
            metrics = report.metrics.get(paper, {}).get(model)
            if metrics:
                print(f"  #{rank} {model}: SSE={metrics.final_best_sse:,.0f}, "
                      f"IoU={metrics.final_best_iou:.4f}")


if __name__ == "__main__":
    main()
