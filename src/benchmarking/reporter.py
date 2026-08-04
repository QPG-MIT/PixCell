"""
Report generator: create comparison reports in multiple formats.
"""

import json
from pathlib import Path
from typing import List

from .aggregator import ComparisonReport, ResultsAggregator


class ReportGenerator:
    """Generates benchmark comparison reports."""

    def __init__(self, report: ComparisonReport, aggregator: ResultsAggregator):
        self.report = report
        self.aggregator = aggregator

    def generate_json(self, output_path: Path):
        """Save raw comparison data as JSON."""
        data = self.aggregator.to_dict(self.report)
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2, default=self._json_default)

    def _json_default(self, obj):
        """Handle non-serializable objects."""
        if hasattr(obj, '__dict__'):
            return obj.__dict__
        return str(obj)

    def generate_markdown(self, output_path: Path):
        """Generate markdown comparison report."""
        lines = [
            "# GDS Generation Benchmark Report",
            "",
            f"**Timestamp:** {self.report.timestamp}",
            f"**Papers tested:** {', '.join(self.report.papers)}",
            f"**Models tested:** {len(self.report.models)}",
            "",
            "---",
            "",
            "## Summary",
            "",
            f"**Best model by SSE:** {self.report.overall_best_by_sse or 'N/A'}",
            f"**Best model by IoU:** {self.report.overall_best_by_iou or 'N/A'}",
            "",
        ]

        # Per-paper sections
        for paper in self.report.papers:
            lines.extend(self._generate_paper_section(paper))

        # Overall comparison table
        lines.extend(self._generate_overall_comparison())

        with open(output_path, "w") as f:
            f.write("\n".join(lines))

    def _generate_paper_section(self, paper: str) -> List[str]:
        """Generate markdown section for a single paper."""
        lines = [
            "---",
            "",
            f"## {paper}",
            "",
        ]

        paper_metrics = self.report.metrics.get(paper, {})
        if not paper_metrics:
            lines.append("*No results available*")
            return lines

        # Rankings by SSE
        sse_rankings = self.report.sse_rankings.get(paper, [])
        lines.extend([
            "### Rankings by SSE (lower is better)",
            "",
            "| Rank | Model | Best SSE | Mean SSE | Improvement |",
            "|------|-------|----------|----------|-------------|",
        ])

        for rank, model_name in enumerate(sse_rankings, 1):
            m = paper_metrics.get(model_name)
            if m and not m.error:
                improvement = f"{m.phase2_improvement_pct:+.1f}%" if m.phase2_improvement_pct else "-"
                lines.append(
                    f"| {rank} | {model_name} | {m.final_best_sse:,.0f} | "
                    f"{m.phase1_mean_sse:,.0f} | {improvement} |"
                )

        # Rankings by IoU
        iou_rankings = self.report.iou_rankings.get(paper, [])
        lines.extend([
            "",
            "### Rankings by IoU (higher is better)",
            "",
            "| Rank | Model | Best IoU | Mean IoU |",
            "|------|-------|----------|----------|",
        ])

        for rank, model_name in enumerate(iou_rankings, 1):
            m = paper_metrics.get(model_name)
            if m and not m.error:
                lines.append(
                    f"| {rank} | {model_name} | {m.final_best_iou:.4f} | "
                    f"{m.phase1_mean_iou:.4f} |"
                )

        # Detailed metrics table
        lines.extend([
            "",
            "### Detailed Metrics",
            "",
            "| Model | P1 Runs | P1 Success | P2 Runs | Final SSE | Final IoU |",
            "|-------|---------|------------|---------|-----------|-----------|",
        ])

        for model_name in self.report.models:
            m = paper_metrics.get(model_name)
            if m:
                if m.error:
                    lines.append(f"| {model_name} | ERROR | - | - | - | - |")
                else:
                    success_rate = f"{m.phase1_turn2_success}/{m.phase1_runs}"
                    sse_str = f"{m.final_best_sse:,.0f}" if m.final_best_sse is not None else "N/A"
                    iou_str = f"{m.final_best_iou:.4f}" if m.final_best_iou is not None else "N/A"
                    lines.append(
                        f"| {model_name} | {m.phase1_runs} | {success_rate} | "
                        f"{m.phase2_runs} | {sse_str} | {iou_str} |"
                    )

        # Telemetry / Efficiency table
        lines.extend([
            "",
            "### Efficiency Metrics",
            "",
            "| Model | Total Tokens | Avg Tokens/Run | API Calls | Total Time | Avg Time/Run |",
            "|-------|--------------|----------------|-----------|------------|--------------|",
        ])

        for model_name in self.report.models:
            m = paper_metrics.get(model_name)
            if m:
                if m.error:
                    lines.append(f"| {model_name} | ERROR | - | - | - | - |")
                elif m.total_tokens > 0:
                    total_time = f"{m.total_duration_seconds:.1f}s" if m.total_duration_seconds else "-"
                    avg_time = f"{m.avg_duration_per_run:.1f}s" if m.avg_duration_per_run else "-"
                    lines.append(
                        f"| {model_name} | {m.total_tokens:,} | {m.avg_tokens_per_run:,.0f} | "
                        f"{m.total_api_calls} | {total_time} | {avg_time} |"
                    )
                else:
                    lines.append(f"| {model_name} | - | - | - | - | - |")

        lines.append("")
        return lines

    def _generate_overall_comparison(self) -> List[str]:
        """Generate overall comparison across all papers."""
        lines = [
            "---",
            "",
            "## Overall Comparison",
            "",
            "### Best SSE per Paper",
            "",
            "| Model | " + " | ".join(self.report.papers) + " | Avg Rank |",
            "|-------" + "|--------" * len(self.report.papers) + "|----------|",
        ]

        # Calculate average rank for each model
        model_ranks = {model: [] for model in self.report.models}

        for paper in self.report.papers:
            rankings = self.report.sse_rankings.get(paper, [])
            for rank, model in enumerate(rankings, 1):
                if model in model_ranks:
                    model_ranks[model].append(rank)

        # Sort models by average rank
        models_sorted = sorted(
            self.report.models,
            key=lambda m: sum(model_ranks[m]) / len(model_ranks[m]) if model_ranks[m] else float('inf')
        )

        for model in models_sorted:
            row = f"| {model} |"
            for paper in self.report.papers:
                rankings = self.report.sse_rankings.get(paper, [])
                if model in rankings:
                    rank = rankings.index(model) + 1
                    row += f" #{rank} |"
                else:
                    row += " - |"

            avg_rank = sum(model_ranks[model]) / len(model_ranks[model]) if model_ranks[model] else float('inf')
            row += f" {avg_rank:.1f} |"
            lines.append(row)

        # Overall efficiency comparison
        lines.extend([
            "",
            "### Overall Efficiency",
            "",
            "| Model | Total Tokens | Total API Calls | Total Time | Avg SSE |",
            "|-------|--------------|-----------------|------------|---------|",
        ])

        # Aggregate across all papers
        model_totals = {}
        for model in self.report.models:
            totals = {"tokens": 0, "calls": 0, "time": 0.0, "sse_values": []}
            for paper in self.report.papers:
                m = self.report.metrics.get(paper, {}).get(model)
                if m and not m.error:
                    totals["tokens"] += m.total_tokens
                    totals["calls"] += m.total_api_calls
                    totals["time"] += m.total_duration_seconds
                    if m.final_best_sse is not None and m.final_best_sse < float('inf'):
                        totals["sse_values"].append(m.final_best_sse)
            model_totals[model] = totals

        # Sort by average SSE
        models_by_sse = sorted(
            self.report.models,
            key=lambda m: (
                sum(model_totals[m]["sse_values"]) / len(model_totals[m]["sse_values"])
                if model_totals[m]["sse_values"] else float('inf')
            )
        )

        for model in models_by_sse:
            t = model_totals[model]
            if t["sse_values"]:
                avg_sse = sum(t["sse_values"]) / len(t["sse_values"])
                total_time = f"{t['time']:.1f}s" if t["time"] else "-"
                lines.append(
                    f"| {model} | {t['tokens']:,} | {t['calls']} | {total_time} | {avg_sse:,.0f} |"
                )
            else:
                lines.append(f"| {model} | - | - | - | - |")

        lines.append("")
        return lines

    def generate_all(self, output_dir: Path):
        """Generate all report formats."""
        self.generate_json(output_dir / "comparison_report.json")
        self.generate_markdown(output_dir / "comparison_report.md")
