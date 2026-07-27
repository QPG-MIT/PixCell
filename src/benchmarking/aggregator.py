"""
Results aggregator: collect and compare benchmark results across models.
"""

import json
import statistics
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ModelMetrics:
    """Aggregated metrics for a single model on a single paper."""
    model_name: str
    model_key: str
    family: str
    paper: str

    # Phase 1 metrics
    phase1_runs: int = 0
    phase1_turn1_success: int = 0
    phase1_turn2_success: int = 0
    phase1_best_sse: float = float('inf')
    phase1_mean_sse: float = float('inf')
    phase1_median_sse: float = float('inf')
    phase1_stddev_sse: float = 0.0
    phase1_best_iou: float = 0.0
    phase1_mean_iou: float = 0.0

    # Phase 2 metrics
    phase2_runs: int = 0
    phase2_best_sse: float = float('inf')
    phase2_best_iou: float = 0.0
    phase2_improvement_pct: float = 0.0

    # Final best (from Phase 2 if available, else Phase 1)
    final_best_sse: float = float('inf')
    final_best_iou: float = 0.0

    # Telemetry metrics (from new telemetry_summary.json)
    total_tokens: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    avg_tokens_per_run: float = 0.0
    total_api_calls: int = 0
    total_duration_seconds: float = 0.0
    avg_duration_per_run: float = 0.0
    phase1_duration_seconds: float = 0.0
    phase2_duration_seconds: float = 0.0

    # Error info
    error: Optional[str] = None


@dataclass
class ComparisonReport:
    """Cross-model comparison report."""
    timestamp: str
    papers: List[str]
    models: List[str]
    metrics: Dict[str, Dict[str, ModelMetrics]] = field(default_factory=dict)
    sse_rankings: Dict[str, List[str]] = field(default_factory=dict)
    iou_rankings: Dict[str, List[str]] = field(default_factory=dict)
    overall_best_by_sse: Optional[str] = None
    overall_best_by_iou: Optional[str] = None


class ResultsAggregator:
    """Aggregates benchmark results for comparison."""

    def __init__(self, benchmark_dir: Path):
        self.benchmark_dir = Path(benchmark_dir)

    def aggregate(self) -> ComparisonReport:
        """Load and aggregate all results from a benchmark run."""
        # Load config
        config_path = self.benchmark_dir / "config.json"
        if not config_path.exists():
            raise ValueError(f"No config.json found in {self.benchmark_dir}")

        with open(config_path) as f:
            config = json.load(f)

        papers = config["papers"]
        model_names = [m["name"] for m in config["models"]]

        report = ComparisonReport(
            timestamp=self.benchmark_dir.name,
            papers=papers,
            models=model_names,
        )

        # Aggregate metrics for each paper
        for paper in papers:
            report.metrics[paper] = {}
            paper_dir = self.benchmark_dir / paper

            if not paper_dir.exists():
                continue

            for model_dir in paper_dir.iterdir():
                if not model_dir.is_dir():
                    continue

                metrics = self._aggregate_model(paper, model_dir)
                if metrics:
                    report.metrics[paper][metrics.model_name] = metrics

        # Compute rankings
        report.sse_rankings = self._compute_rankings(report.metrics, "final_best_sse", reverse=False)
        report.iou_rankings = self._compute_rankings(report.metrics, "final_best_iou", reverse=True)

        # Find overall best
        report.overall_best_by_sse = self._find_overall_best(report.sse_rankings)
        report.overall_best_by_iou = self._find_overall_best(report.iou_rankings)

        return report

    def _aggregate_model(self, paper: str, model_dir: Path) -> Optional[ModelMetrics]:
        """Aggregate metrics for a single model."""
        summary_path = model_dir / "model_summary.json"
        if not summary_path.exists():
            return None

        with open(summary_path) as f:
            summary = json.load(f)

        # Load telemetry data if available
        phase1_telemetry = {}
        phase2_telemetry = {}
        phase1_telemetry_path = model_dir / "phase1" / "telemetry_summary.json"
        phase2_telemetry_path = model_dir / "phase2" / "telemetry_summary.json"

        if phase1_telemetry_path.exists():
            with open(phase1_telemetry_path) as f:
                phase1_telemetry = json.load(f)

        if phase2_telemetry_path.exists():
            with open(phase2_telemetry_path) as f:
                phase2_telemetry = json.load(f)

        # Check for error
        if summary.get("error"):
            return ModelMetrics(
                model_name=summary.get("model", model_dir.name),
                model_key=summary.get("model_key", ""),
                family=summary.get("family", ""),
                paper=paper,
                error=summary.get("error"),
            )

        # Extract Phase 1 metrics
        phase1 = summary.get("phase1", {})
        phase1_sse_values = []
        phase1_iou_values = []

        ranked_by_sse = phase1.get("ranked_by_sse", [])
        for r in ranked_by_sse:
            sse = r.get("final_sse")
            iou = r.get("final_iou")
            if sse is not None:
                phase1_sse_values.append(sse)
            if iou is not None:
                phase1_iou_values.append(iou)

        # Extract Phase 2 metrics
        phase2 = summary.get("phase2", {})

        # Calculate improvement
        phase1_best_sse = min(phase1_sse_values) if phase1_sse_values else float('inf')
        phase2_best_sse = phase2.get("best_final_sse", float('inf'))

        if phase1_best_sse > 0 and phase2_best_sse < float('inf'):
            improvement_pct = (phase1_best_sse - phase2_best_sse) / phase1_best_sse * 100
        else:
            improvement_pct = 0.0

        # Aggregate telemetry (nested under aggregate_usage and aggregate_attempts)
        p1_usage = phase1_telemetry.get("aggregate_usage", {})
        p2_usage = phase2_telemetry.get("aggregate_usage", {})
        p1_attempts = phase1_telemetry.get("aggregate_attempts", {})
        p2_attempts = phase2_telemetry.get("aggregate_attempts", {})

        p1_tokens = p1_usage.get("total_tokens", 0)
        p2_tokens = p2_usage.get("total_tokens", 0)
        p1_input = p1_usage.get("total_input_tokens", 0)
        p2_input = p2_usage.get("total_input_tokens", 0)
        p1_output = p1_usage.get("total_output_tokens", 0)
        p2_output = p2_usage.get("total_output_tokens", 0)
        p1_calls = p1_attempts.get("total_api_calls", 0)
        p2_calls = p2_attempts.get("total_api_calls", 0)
        p1_duration = phase1_telemetry.get("exploration_duration_seconds", 0.0)
        p2_duration = phase2_telemetry.get("exploration_duration_seconds", 0.0)

        total_runs = phase1.get("runs_tested", 0) + phase2.get("runs_processed", 0)

        return ModelMetrics(
            model_name=summary.get("model", model_dir.name),
            model_key=summary.get("model_key", ""),
            family=summary.get("family", ""),
            paper=paper,
            # Phase 1
            phase1_runs=phase1.get("runs_tested", 0),
            phase1_turn1_success=phase1.get("turn1_successful", 0),
            phase1_turn2_success=phase1.get("turn2_successful", 0),
            phase1_best_sse=phase1_best_sse,
            phase1_mean_sse=statistics.mean(phase1_sse_values) if phase1_sse_values else float('inf'),
            phase1_median_sse=statistics.median(phase1_sse_values) if phase1_sse_values else float('inf'),
            phase1_stddev_sse=statistics.stdev(phase1_sse_values) if len(phase1_sse_values) > 1 else 0.0,
            phase1_best_iou=max(phase1_iou_values) if phase1_iou_values else 0.0,
            phase1_mean_iou=statistics.mean(phase1_iou_values) if phase1_iou_values else 0.0,
            # Phase 2
            phase2_runs=phase2.get("runs_processed", 0),
            phase2_best_sse=phase2_best_sse if phase2_best_sse != float('inf') else phase1_best_sse,
            phase2_best_iou=phase2.get("best_final_iou", 0.0),
            phase2_improvement_pct=improvement_pct,
            # Final
            final_best_sse=summary.get("best_sse", phase1_best_sse),
            final_best_iou=summary.get("best_iou", 0.0),
            # Telemetry
            total_tokens=p1_tokens + p2_tokens,
            total_input_tokens=p1_input + p2_input,
            total_output_tokens=p1_output + p2_output,
            avg_tokens_per_run=(p1_tokens + p2_tokens) / total_runs if total_runs > 0 else 0.0,
            total_api_calls=p1_calls + p2_calls,
            total_duration_seconds=p1_duration + p2_duration,
            avg_duration_per_run=(p1_duration + p2_duration) / total_runs if total_runs > 0 else 0.0,
            phase1_duration_seconds=p1_duration,
            phase2_duration_seconds=p2_duration,
        )

    def _compute_rankings(
        self,
        metrics: Dict[str, Dict[str, ModelMetrics]],
        metric_name: str,
        reverse: bool = False
    ) -> Dict[str, List[str]]:
        """Compute model rankings for each paper."""
        rankings = {}

        for paper, paper_metrics in metrics.items():
            # Get (model_name, metric_value) pairs
            values = []
            for model_name, m in paper_metrics.items():
                if m.error:
                    continue
                value = getattr(m, metric_name, None)
                # Skip None values and infinity for ranking
                if value is None or value == float('inf'):
                    continue
                values.append((model_name, value))

            # Sort (lower is better for SSE, higher is better for IoU)
            if values:
                values.sort(key=lambda x: x[1], reverse=reverse)
            rankings[paper] = [name for name, _ in values]

        return rankings

    def _find_overall_best(self, rankings: Dict[str, List[str]]) -> Optional[str]:
        """Find model that ranks best across all papers."""
        if not rankings:
            return None

        # Simple approach: count first-place finishes
        first_place_counts: Dict[str, int] = {}
        for paper, ranked in rankings.items():
            if ranked:
                winner = ranked[0]
                first_place_counts[winner] = first_place_counts.get(winner, 0) + 1

        if not first_place_counts:
            return None

        # Return model with most first-place finishes
        return max(first_place_counts.items(), key=lambda x: x[1])[0]

    def to_dict(self, report: ComparisonReport) -> Dict[str, Any]:
        """Convert report to JSON-serializable dict."""
        return {
            "timestamp": report.timestamp,
            "papers": report.papers,
            "models": report.models,
            "metrics": {
                paper: {
                    model: {
                        "model_name": m.model_name,
                        "model_key": m.model_key,
                        "family": m.family,
                        "phase1_runs": m.phase1_runs,
                        "phase1_turn1_success": m.phase1_turn1_success,
                        "phase1_turn2_success": m.phase1_turn2_success,
                        "phase1_best_sse": m.phase1_best_sse,
                        "phase1_mean_sse": m.phase1_mean_sse,
                        "phase1_median_sse": m.phase1_median_sse,
                        "phase1_stddev_sse": m.phase1_stddev_sse,
                        "phase1_best_iou": m.phase1_best_iou,
                        "phase1_mean_iou": m.phase1_mean_iou,
                        "phase2_runs": m.phase2_runs,
                        "phase2_best_sse": m.phase2_best_sse,
                        "phase2_best_iou": m.phase2_best_iou,
                        "phase2_improvement_pct": m.phase2_improvement_pct,
                        "final_best_sse": m.final_best_sse,
                        "final_best_iou": m.final_best_iou,
                        "total_tokens": m.total_tokens,
                        "total_input_tokens": m.total_input_tokens,
                        "total_output_tokens": m.total_output_tokens,
                        "avg_tokens_per_run": m.avg_tokens_per_run,
                        "total_api_calls": m.total_api_calls,
                        "total_duration_seconds": m.total_duration_seconds,
                        "avg_duration_per_run": m.avg_duration_per_run,
                        "phase1_duration_seconds": m.phase1_duration_seconds,
                        "phase2_duration_seconds": m.phase2_duration_seconds,
                        "error": m.error,
                    }
                    for model, m in paper_metrics.items()
                }
                for paper, paper_metrics in report.metrics.items()
            },
            "sse_rankings": report.sse_rankings,
            "iou_rankings": report.iou_rankings,
            "overall_best_by_sse": report.overall_best_by_sse,
            "overall_best_by_iou": report.overall_best_by_iou,
        }
