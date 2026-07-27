#!/usr/bin/env python3
"""
OpenAI-only benchmark for HOMI GDS generation.

Benchmarks GPT-5.2 and GPT-5 models with appropriate parallelism, adjusted for
OpenAI's rate limits (lower than Gemini).

Models (Massive Run Selection):
  - GPT-5.2 (gpt-5.2) - reasoning: none/low/medium/high/xhigh
  - GPT-5 (gpt-5) - reasoning: minimal/low/medium/high

Usage:
    python -m benchmarking.openai_benchmark --papers 1x2_coupler 2_004629
    python -m benchmarking.openai_benchmark --papers paper1 paper2 paper3 paper4
    python -m benchmarking.openai_benchmark --dry-run --papers 1x2_coupler
"""

import argparse
import shutil
import sys
from pathlib import Path
from typing import List

from homi.paths import projects_dir

from benchmarking.config import (
    BenchmarkConfig,
    BenchmarkModel,
    Phase1Config,
    Phase2Config,
)
from benchmarking.runner import BenchmarkRunner
from benchmarking.aggregator import ResultsAggregator
from benchmarking.reporter import ReportGenerator


def test_api_connectivity(models: List[BenchmarkModel]) -> bool:
    """Test API connectivity with a simple request.

    Args:
        models: List of models to test

    Returns:
        True if all tests passed, False otherwise
    """
    from homi.model_client import create_client, ModelConfig, VisionMessage

    print("=" * 70)
    print("API CONNECTIVITY TEST")
    print("=" * 70)

    all_passed = True

    for model in models:
        model_id = model.model_key.split("/")[-1]
        print(f"\nTesting {model.name} ({model.model_key})...")

        try:
            # Create client
            client, actual_model_id = create_client(model.model_key)

            # Create a simple test message (no image)
            config = ModelConfig(
                temperature=1.0,
                max_tokens=100,
                thinking_mode="low" if model.supports_thinking else None,
            )

            messages = [
                VisionMessage(
                    role="user",
                    text="Say 'API test successful' in exactly 4 words."
                )
            ]

            # Make API call
            response = client.generate(messages, config, actual_model_id)

            # Check response
            if response.text and len(response.text) > 0:
                print(f"  [OK] Response received ({len(response.text)} chars)")
                print(f"       Response: {response.text[:100]}...")
                if response.usage:
                    print(f"       Tokens: {response.usage.get('total_tokens', 'N/A')}")
            else:
                print(f"  [WARN] Empty response received")
                all_passed = False

        except Exception as e:
            print(f"  [FAIL] {type(e).__name__}: {e}")
            all_passed = False

    print("\n" + "=" * 70)
    if all_passed:
        print("All API tests PASSED")
    else:
        print("Some API tests FAILED - check errors above")
    print("=" * 70)

    return all_passed


# =============================================================================
# OPENAI MODELS - 5 selected models for benchmarking
# =============================================================================
# OpenAI model characteristics:
#   - No deterministic seeds (supports_seed=False for all)
#   - GPT-5 series and GPT-4.1 series support extended thinking
#   - GPT-4o series does NOT support extended thinking
#   - Vision/multimodal input supported
#   - Rate limits are tier-dependent (conservative defaults)
# =============================================================================

OPENAI_MODELS: List[BenchmarkModel] = [
    # GPT-5 Series (Reasoning Models) - Selected for massive benchmark run
    # GPT-5.2 - reasoning effort: none, low, medium, high, xhigh (max: xhigh)
    BenchmarkModel(
        name="GPT-5.2",
        model_key="openai/gpt-5.2",
        family="openai",
        supports_seed=False,
        supports_thinking=True,
    ),
    # GPT-5 - reasoning effort: minimal, low, medium, high (max: high)
    BenchmarkModel(
        name="GPT-5",
        model_key="openai/gpt-5",
        family="openai",
        supports_seed=False,
        supports_thinking=True,
    ),
]


def create_openai_config(
    papers: List[str],
    num_seeds: int = 15,
    base_seed: int = 1333,
    phase1_parallel: int = 8,
    phase2_top_k: int = 3,
    phase2_parallel: int = 3,
    phase2_turns: int = 3,
    output_dir: Path = Path("benchmark_results"),
    projects_dir: Path = projects_dir(),
    michaelangelo_dir: Path = Path("michaelangelo"),
    reasoning_effort: str = "medium",
) -> BenchmarkConfig:
    """Create benchmark config for OpenAI models.

    Default settings are conservative for OpenAI's rate limits:
    - Phase 1: 4 seeds in parallel (vs 15 for Gemini)
    - Phase 2: 2 seeds in parallel (vs 5 for Gemini)
    - 2 parallel (paper × model) combinations

    Note: OpenAI models do NOT support deterministic seeds, so each run
    will produce different results. The base_seed is still used for
    run identification but doesn't affect model behavior.
    """
    # Conservative parallel models: OpenAI has stricter rate limits
    max_parallel = min(len(papers) * len(OPENAI_MODELS), 2)

    return BenchmarkConfig(
        papers=papers,
        models=OPENAI_MODELS.copy(),
        phase1=Phase1Config(
            num_seeds=num_seeds,
            base_seed=base_seed,
            num_parallel=phase1_parallel,
            max_attempts=3,
            reasoning_effort=reasoning_effort,
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
        clean_models: List of model keys to clean (e.g., 'gpt-5.2') or ['all']
        projects_dir: Path to projects directory
    """
    clean_all = "all" in clean_models

    for paper in papers:
        for model in models:
            # Extract model ID from key (e.g., "openai/gpt-5.2" -> "gpt-5.2")
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
        description="Run OpenAI-only GDS generation benchmark",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
OpenAI Models Benchmarked (Massive Run Selection):
  GPT-5 Series (Reasoning Models):
    - GPT-5.2 (gpt-5.2) - reasoning: none/low/medium/high/xhigh
    - GPT-5 (gpt-5) - reasoning: minimal/low/medium/high

Note: OpenAI models do NOT support deterministic seeds. Each run produces
different results, making benchmarking less reproducible than Gemini models.

Examples:
  # Run on default papers
  python -m benchmarking.openai_benchmark

  # Run on specific papers
  python -m benchmarking.openai_benchmark --papers paper1 paper2 paper3 paper4

  # Custom Phase 1 settings (conservative for rate limits)
  python -m benchmarking.openai_benchmark --phase1-seeds 10 --phase1-parallel 2

  # Dry run to validate configuration
  python -m benchmarking.openai_benchmark --dry-run --papers 1x2_coupler

  # Aggregate existing results only
  python -m benchmarking.openai_benchmark --aggregate benchmark_results/2026-01-23_120000
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
        help="Only run specific models (e.g., 'gpt-5.2 gpt-5.2-pro'). "
             "Use model IDs without 'openai/' prefix. Default: run all 2 models."
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
        default=8,
        help="Parallel workers for Phase 1 seeds (default: 8)"
    )
    parser.add_argument(
        "--phase1-base-seed",
        type=int,
        default=1333,
        help="Base seed for Phase 1 (default: 1333, used for run IDs only)"
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
    parser.add_argument(
        "--reasoning-effort",
        type=str,
        default="medium",
        choices=["high", "medium", "low"],
        help="Reasoning/thinking effort level (default: medium)"
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
        default=Path("michaelangelo"),
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
             "Use model keys like 'gpt-5.2' or 'all' for all models."
    )

    # Test API connectivity
    parser.add_argument(
        "--test-api",
        action="store_true",
        help="Test API connectivity with a simple request before running benchmark. "
             "Verifies model availability and response parsing."
    )

    args = parser.parse_args()

    # Aggregate-only mode
    if args.aggregate:
        print(f"Aggregating results from: {args.aggregate}")
        aggregate_results(args.aggregate)
        return

    # Test API connectivity mode
    if args.test_api:
        # Filter models if --models specified
        models_to_test = OPENAI_MODELS.copy()
        if args.models:
            models_to_test = [
                m for m in models_to_test
                if m.model_key.split("/")[-1] in args.models
            ]
            if not models_to_test:
                print(f"ERROR: No models matched filter: {args.models}")
                print("Available models:")
                for m in OPENAI_MODELS:
                    print(f"  - {m.model_key.split('/')[-1]}")
                return

        success = test_api_connectivity(models_to_test)
        sys.exit(0 if success else 1)

    # Create config
    config = create_openai_config(
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
        reasoning_effort=args.reasoning_effort,
    )

    # Filter models if --models specified
    if args.models:
        filtered_models = []
        for model in config.models:
            model_id = model.model_key.split("/")[-1]
            # Use exact match to avoid gpt-5.2 matching gpt-5.2-pro
            if model_id in args.models:
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
    print("HOMI OpenAI-Only Benchmark")
    print("=" * 70)
    print(f"Papers: {config.papers}")
    print(f"Models ({len(config.models)}):")
    for m in config.models:
        thinking_status = "thinking" if m.supports_thinking else "no thinking"
        print(f"  - {m.name} ({m.model_key}) [{thinking_status}]")
    print(f"Parallel (paper x model) combinations: {config.num_parallel_models}")
    print(f"Phase 1: {config.phase1.num_seeds} seeds, {config.phase1.num_parallel} parallel")
    print(f"Phase 2: top {config.phase2.top_k}, {config.phase2.additional_turns} turns, "
          f"{config.phase2.num_parallel} parallel")
    print(f"Output: {config.output_dir}")
    print()
    print("NOTE: OpenAI models do NOT support deterministic seeds.")
    print("      Results will vary between runs.")
    print("=" * 70)

    # Estimate
    total_phase1 = len(config.papers) * len(config.models) * config.phase1.num_seeds
    total_phase2 = len(config.papers) * len(config.models) * config.phase2.top_k
    print(f"\nEstimated API calls:")
    print(f"  Phase 1: {total_phase1} requests (max concurrent: {config.phase1.num_parallel})")
    print(f"  Phase 2: {total_phase2} requests (max concurrent: {config.phase2.num_parallel})")
    print(f"  Note: OpenAI rate limits are stricter - expect longer run times")
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
    print("\nStarting OpenAI benchmark...\n")
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

    print(f"  [OK] comparison_report.json")
    print(f"  [OK] comparison_report.md")

    # Print summary
    print("\n" + "=" * 70)
    print("OPENAI BENCHMARK RESULTS")
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
