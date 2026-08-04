#!/usr/bin/env python3
"""
Gemini-only benchmark for HOMI GDS generation.

Benchmarks all 5 Gemini models with maximum parallelism, optimized for
high rate limits (2K-30K RPM per model).

Usage:
    python -m benchmarking.gemini_benchmark --papers 1x2_coupler 2_004629
    python -m benchmarking.gemini_benchmark --papers paper1 paper2 paper3 paper4
    python -m benchmarking.gemini_benchmark --dry-run --papers 1x2_coupler
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
# GEMINI MODELS - All 5 models from the registry
# =============================================================================
# All Gemini models support:
#   - Deterministic seeds (supports_seed=True)
#   - Extended thinking with levels: "none", "low", "medium", "high"
#   - Vision/multimodal input
#   - 65536 max output tokens
# =============================================================================

GEMINI_MODELS: List[BenchmarkModel] = [
    BenchmarkModel(
        name="Gemini 3.1 Pro",
        model_key="gemini/gemini-3.1-pro-preview",
        family="gemini",
        supports_seed=True,
        supports_thinking=True,
    ),
    BenchmarkModel(
        name="Gemini 3.1 Flash-Lite",
        model_key="gemini/gemini-3.1-flash-lite-preview",
        family="gemini",
        supports_seed=True,
        supports_thinking=True,
    ),
    BenchmarkModel(
        name="Gemini 3 Pro",
        model_key="gemini/gemini-3-pro-preview",
        family="gemini",
        supports_seed=True,
        supports_thinking=True,
    ),
    BenchmarkModel(
        name="Gemini 3 Flash",
        model_key="gemini/gemini-3-flash-preview",
        family="gemini",
        supports_seed=True,
        supports_thinking=True,
    ),
    BenchmarkModel(
        name="Gemini 2.5 Pro",
        model_key="gemini/gemini-2.5-pro",
        family="gemini",
        supports_seed=True,
        supports_thinking=True,
    ),
    BenchmarkModel(
        name="Gemini 2.5 Flash",
        model_key="gemini/gemini-2.5-flash",
        family="gemini",
        supports_seed=True,
        supports_thinking=True,
    ),
    BenchmarkModel(
        name="Gemini 2.0 Flash",
        model_key="gemini/gemini-2.0-flash",
        family="gemini",
        supports_seed=True,
        supports_thinking=False,  # Gemini 2.0 does not support thinking
    ),
]


def create_gemini_config(
    papers: List[str],
    num_seeds: int = 15,
    base_seed: int = 1333,
    phase1_parallel: int = 15,
    phase2_top_k: int = 3,
    phase2_parallel: int = 3,
    phase2_turns: int = 3,
    output_dir: Path = Path("benchmark_results"),
    projects_dir: Path = projects_dir(),
    michaelangelo_dir: Path = michaelangelo_dir(),
) -> BenchmarkConfig:
    """Create optimized benchmark config for Gemini models.

    Default settings maximize parallelism for Gemini's high rate limits:
    - Phase 1: All 15 seeds run in parallel
    - Phase 2: All top-5 seeds run in parallel
    - All (paper × model) combinations run in parallel
    """
    # Calculate max parallel models: papers × 5 Gemini models
    max_parallel = len(papers) * len(GEMINI_MODELS)

    return BenchmarkConfig(
        papers=papers,
        models=GEMINI_MODELS.copy(),
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
        clean_models: List of model keys to clean (e.g., 'gemini-2.5-pro') or ['all']
        projects_dir: Path to projects directory
    """
    clean_all = "all" in clean_models

    for paper in papers:
        for model in models:
            # Extract model ID from key (e.g., "gemini/gemini-2.5-pro" -> "gemini-2.5-pro")
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
        description="Run Gemini-only GDS generation benchmark",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Gemini Models Benchmarked:
  - Gemini 3 Pro (gemini-3-pro-preview)
  - Gemini 3 Flash (gemini-3-flash-preview)
  - Gemini 2.5 Pro (gemini-2.5-pro)
  - Gemini 2.5 Flash (gemini-2.5-flash)
  - Gemini 2.0 Flash (gemini-2.0-flash)

Examples:
  # Run on default papers
  python -m benchmarking.gemini_benchmark

  # Run on specific papers with max parallelism
  python -m benchmarking.gemini_benchmark --papers paper1 paper2 paper3 paper4

  # Custom Phase 1 settings
  python -m benchmarking.gemini_benchmark --phase1-seeds 20 --phase1-parallel 20

  # Dry run to validate configuration
  python -m benchmarking.gemini_benchmark --dry-run --papers 1x2_coupler

  # Aggregate existing results only
  python -m benchmarking.gemini_benchmark --aggregate benchmark_results/2026-01-23_120000
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
        help="Only run specific models (e.g., 'gemini-2.5-pro gemini-2.5-flash'). "
             "Use model IDs without 'gemini/' prefix. Default: run all 5 models."
    )

    # Phase 1 config
    parser.add_argument(
        "--phase1-seeds",
        type=int,
        default=15,
        help="Number of seeds for Phase 1 (default: 15)"
    )
    parser.add_argument(
        "--phase1-parallel",
        type=int,
        default=15,
        help="Parallel workers for Phase 1 seeds (default: 15 = all parallel)"
    )
    parser.add_argument(
        "--phase1-base-seed",
        type=int,
        default=1333,
        help="Base seed for Phase 1 (default: 1333)"
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
        help="Parallel workers for Phase 2 seeds (default: 3 = all parallel)"
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
             "Use model keys like 'gemini-2.5-pro' or 'all' for all models."
    )

    args = parser.parse_args()

    # Aggregate-only mode
    if args.aggregate:
        print(f"Aggregating results from: {args.aggregate}")
        aggregate_results(args.aggregate)
        return

    # Create config
    config = create_gemini_config(
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
        config.num_parallel_models = len(args.papers) * len(filtered_models)

    # Print configuration
    print("=" * 70)
    print("HOMI Gemini-Only Benchmark")
    print("=" * 70)
    print(f"Papers: {config.papers}")
    print(f"Models ({len(config.models)}):")
    for m in config.models:
        print(f"  - {m.name} ({m.model_key})")
    print(f"Parallel (paper×model) combinations: {config.num_parallel_models}")
    print(f"Phase 1: {config.phase1.num_seeds} seeds, {config.phase1.num_parallel} parallel")
    print(f"Phase 2: top {config.phase2.top_k}, {config.phase2.additional_turns} turns, "
          f"{config.phase2.num_parallel} parallel")
    print(f"Output: {config.output_dir}")
    print("=" * 70)

    # Estimate
    total_phase1 = len(config.papers) * len(config.models) * config.phase1.num_seeds
    total_phase2 = len(config.papers) * len(config.models) * config.phase2.top_k
    print("\nEstimated API calls:")
    print(f"  Phase 1: {total_phase1} requests (max concurrent: {total_phase1})")
    print(f"  Phase 2: {total_phase2} requests (max concurrent: {total_phase2})")
    print("  Estimated time: ~15-20 minutes with full parallelism")
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
    print("\nStarting Gemini benchmark...\n")
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
    print("GEMINI BENCHMARK RESULTS")
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
