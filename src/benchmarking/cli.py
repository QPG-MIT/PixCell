#!/usr/bin/env python3
"""
Command-line interface for the HOMI multi-model benchmark.

Usage:
    python -m benchmarking.cli --papers final_1 final_2
    python -m benchmarking.cli --models gemini claude --phase1-seeds 10
    python -m benchmarking.cli --aggregate benchmark_results/2026-01-23_143052
"""

import argparse
import sys
from pathlib import Path

from homi.paths import michaelangelo_dir, workspace_root

from benchmarking.config import (
    BenchmarkConfig,
    BenchmarkModel,
    Phase1Config,
    Phase2Config,
    BENCHMARK_MODELS,
)
from benchmarking.runner import BenchmarkRunner
from benchmarking.aggregator import ResultsAggregator
from benchmarking.reporter import ReportGenerator


def main():
    parser = argparse.ArgumentParser(
        description="Run multi-model GDS generation benchmark",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run full benchmark on default papers
  python -m benchmarking.cli

  # Run with specific papers
  python -m benchmarking.cli --papers final_1 final_2

  # Run with specific model families
  python -m benchmarking.cli --families gemini claude openai

  # Run with custom Phase 1 config
  python -m benchmarking.cli --phase1-seeds 30 --phase1-parallel 10

  # Only aggregate existing results
  python -m benchmarking.cli --aggregate benchmark_results/2026-01-23_143052
        """
    )

    # Run mode
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
        default=[f"final_{i}" for i in range(1, 9)],
        help="Papers to benchmark (project directory names)"
    )

    # Model selection
    parser.add_argument(
        "--families",
        nargs="+",
        default=None,
        choices=["gemini", "claude", "openai", "kimi", "qwen", "grok"],
        help="Model families to include (default: all)"
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
        help="Parallel workers for Phase 1 (default: 8)"
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
        default=5,
        help="Number of top seeds by SSE for Phase 2 (default: 5)"
    )
    parser.add_argument(
        "--phase2-parallel",
        type=int,
        default=4,
        help="Parallel workers for Phase 2 (default: 4)"
    )
    parser.add_argument(
        "--phase2-turns",
        type=int,
        default=2,
        help="Additional turns in Phase 2 (default: 2)"
    )

    # Parallelism
    parser.add_argument(
        "--parallel-models",
        type=int,
        default=6,
        help="Number of models to run in parallel (default: 6, all models)"
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
        default=workspace_root() / "data" / "benchmark",
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

    args = parser.parse_args()

    # Aggregate-only mode
    if args.aggregate:
        print(f"Aggregating results from: {args.aggregate}")
        aggregate_results(args.aggregate)
        return

    # Filter models by family
    if args.families:
        models = [m for m in BENCHMARK_MODELS if m.family in args.families]
        if not models:
            print(f"Error: No models found for families: {args.families}")
            sys.exit(1)
    else:
        models = BENCHMARK_MODELS.copy()

    # Build config
    config = BenchmarkConfig(
        papers=args.papers,
        models=models,
        phase1=Phase1Config(
            num_seeds=args.phase1_seeds,
            base_seed=args.phase1_base_seed,
            num_parallel=args.phase1_parallel,
        ),
        phase2=Phase2Config(
            top_k=args.phase2_top,
            num_parallel=args.phase2_parallel,
            additional_turns=args.phase2_turns,
        ),
        num_parallel_models=args.parallel_models,
        output_dir=args.output_dir,
        projects_dir=args.projects_dir,
        michaelangelo_dir=args.michaelangelo_dir,
    )

    # Print configuration
    print("=" * 70)
    print("HOMI Multi-Model Benchmark")
    print("=" * 70)
    print(f"Papers: {config.papers}")
    print(f"Models: {[m.name for m in config.models]} ({config.num_parallel_models} parallel)")
    print(f"Phase 1: {config.phase1.num_seeds} seeds, {config.phase1.num_parallel} parallel")
    print(f"Phase 2: top {config.phase2.top_k}, {config.phase2.additional_turns} turns, {config.phase2.num_parallel} parallel")
    print(f"Output: {config.output_dir}")
    print("=" * 70)

    if args.dry_run:
        print("\nDry run - validating configuration...")
        runner = BenchmarkRunner(config)
        for paper in config.papers:
            try:
                runner._validate_paper(paper)
                print(f"  ✓ {paper} - valid")
            except Exception as e:
                print(f"  ✗ {paper} - {e}")
        print("\nDry run complete.")
        return

    # Run benchmark
    print("\nStarting benchmark...\n")
    runner = BenchmarkRunner(config)
    results = runner.run()

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

    print(f"  ✓ comparison_report.json")
    print(f"  ✓ comparison_report.md")

    # Print summary
    print("\n" + "=" * 70)
    print("RESULTS SUMMARY")
    print("=" * 70)
    print(f"Best by SSE: {report.overall_best_by_sse or 'N/A'}")
    print(f"Best by IoU: {report.overall_best_by_iou or 'N/A'}")

    for paper in report.papers:
        print(f"\n{paper}:")
        rankings = report.sse_rankings.get(paper, [])
        for rank, model in enumerate(rankings[:3], 1):
            metrics = report.metrics.get(paper, {}).get(model)
            if metrics:
                print(f"  #{rank} {model}: SSE={metrics.final_best_sse:,.0f}, IoU={metrics.final_best_iou:.4f}")


if __name__ == "__main__":
    main()
