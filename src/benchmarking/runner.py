"""
Benchmark runner: orchestrates multi-model GDS generation benchmarks.
"""

import json
import logging
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Load environment variables from .env (upward search / checkout / ~/.pixcell/env)
try:
    from homi.paths import load_env
    load_env()
except ImportError:
    pass  # dotenv not installed

from .config import BenchmarkConfig, BenchmarkModel


class BenchmarkRunner:
    """Orchestrates multi-model benchmark runs."""

    def __init__(self, config: BenchmarkConfig):
        self.config = config
        self.timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        self.run_dir = config.output_dir / self.timestamp
        self.results: Dict[str, Dict[str, Any]] = {}
        self.logger = self._setup_logging()

    def _setup_logging(self) -> logging.Logger:
        """Setup logging to file and console."""
        self.run_dir.mkdir(parents=True, exist_ok=True)

        logger = logging.getLogger("benchmark")
        logger.setLevel(logging.INFO)

        # File handler
        fh = logging.FileHandler(self.run_dir / "benchmark.log")
        fh.setLevel(logging.INFO)

        # Console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)

        # Format
        formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)

        logger.addHandler(fh)
        logger.addHandler(ch)

        return logger

    def _validate_environment(self) -> None:
        """Validate environment before running benchmark.

        Checks:
        1. Virtual environment is activated
        2. Critical dependencies are importable (fitz, gdsfactory, homi)

        Raises:
            RuntimeError: If environment is misconfigured
        """
        warnings = []

        # Check venv activation
        if not (hasattr(sys, 'real_prefix') or
                (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)):
            warnings.append(
                "Virtual environment may not be activated. "
                "Run: source .venv/bin/activate"
            )

        # Check critical dependencies
        missing_deps = []
        try:
            import fitz  # noqa: F401
        except ImportError:
            missing_deps.append("fitz (PyMuPDF)")

        try:
            import gdsfactory  # noqa: F401
        except ImportError:
            missing_deps.append("gdsfactory")

        try:
            import homi  # noqa: F401
        except ImportError:
            missing_deps.append("homi")

        if missing_deps:
            raise RuntimeError(
                f"Missing dependencies: {', '.join(missing_deps)}. "
                f"Ensure venv is activated: source .venv/bin/activate"
            )

        # Log warnings but don't fail
        for warning in warnings:
            self.logger.warning(warning)

        self.logger.info("Environment validation passed")

    def run(self) -> Dict[str, Any]:
        """Execute full benchmark across all papers and models."""
        # Validate environment before starting
        self._validate_environment()

        self.logger.info(f"Starting benchmark run: {self.timestamp}")
        self.logger.info(f"Papers: {self.config.papers}")
        self.logger.info(f"Models: {[m.name for m in self.config.models]}")

        # Save config
        config_path = self.run_dir / "config.json"
        with open(config_path, "w") as f:
            json.dump(self.config.to_dict(), f, indent=2)

        # Validate all papers first
        for paper in self.config.papers:
            self._validate_paper(paper)

        # Build list of (paper, model) tasks to run
        tasks: List[Tuple[str, BenchmarkModel]] = []
        for paper in self.config.papers:
            self.results[paper] = {}
            for model in self.config.models:
                # Check if already completed (resumability)
                if self._is_model_complete(paper, model):
                    self.logger.info(f"Skipping {model.name} on {paper} - already completed")
                    self.results[paper][model.name] = self._load_model_results(paper, model)
                else:
                    tasks.append((paper, model))

        if not tasks:
            self.logger.info("All tasks already completed!")
            return self.results

        self.logger.info(f"\nRunning {len(tasks)} model/paper combinations "
                        f"with {self.config.num_parallel_models} parallel models")

        # Run models in parallel
        with ThreadPoolExecutor(max_workers=self.config.num_parallel_models) as executor:
            futures = {
                executor.submit(self._run_model_safe, paper, model): (paper, model)
                for paper, model in tasks
            }

            for future in as_completed(futures):
                paper, model = futures[future]
                try:
                    result = future.result()
                    self.results[paper][model.name] = result
                    status = "SUCCESS" if result.get("success") else "FAILED"
                    self.logger.info(f"[{model.name}] {paper}: {status}")
                except Exception as e:
                    self.logger.error(f"[{model.name}] {paper}: EXCEPTION - {e}")
                    self.results[paper][model.name] = {"error": str(e), "success": False}

        self.logger.info(f"\nBenchmark complete! Results saved to: {self.run_dir}")
        return self.results

    def _run_model_safe(self, paper: str, model: BenchmarkModel) -> Dict[str, Any]:
        """Run model with exception handling (for parallel execution)."""
        try:
            return self._run_model(paper, model)
        except Exception as e:
            self.logger.error(f"[{model.name}] {paper}: ERROR - {e}")
            traceback.print_exc()
            return {"error": str(e), "success": False}

    def _validate_paper(self, paper: str):
        """Validate paper has required files for benchmarking."""
        project_dir = self.config.projects_dir / paper

        if not project_dir.exists():
            raise ValueError(f"Project directory not found: {project_dir}")

        # Check for device_bw.png
        device_bw = project_dir / "device_bw.png"
        if not device_bw.exists():
            raise ValueError(f"device_bw.png not found in {project_dir}")

        # Check for footprint (in state.json or footprint.json)
        state_file = project_dir / "state.json"
        footprint_file = project_dir / "footprint.json"

        if state_file.exists():
            with open(state_file) as f:
                state = json.load(f)
            if "footprint" not in state:
                if not footprint_file.exists():
                    raise ValueError(f"No footprint found in {project_dir}")
        elif not footprint_file.exists():
            raise ValueError(f"No footprint found in {project_dir}")

        self.logger.info(f"Validated paper: {paper}")

    def _get_footprint(self, paper: str) -> tuple:
        """Get footprint dimensions for a paper."""
        project_dir = self.config.projects_dir / paper

        # Try state.json first
        state_file = project_dir / "state.json"
        if state_file.exists():
            with open(state_file) as f:
                state = json.load(f)
            if "footprint" in state:
                fp = state["footprint"]
                return (fp["length_um"], fp["width_um"])

        # Fall back to footprint.json
        footprint_file = project_dir / "footprint.json"
        if footprint_file.exists():
            with open(footprint_file) as f:
                fp = json.load(f)
            if "footprint_um" in fp:
                return tuple(fp["footprint_um"])

        raise ValueError(f"Could not determine footprint for {paper}")

    def _setup_component_dir(self, paper: str, model: BenchmarkModel) -> Path:
        """Setup component directory for a model run."""
        from homi import gds_generation

        project_dir = self.config.projects_dir / paper

        # Model-specific scratch lives under the (gitignored) run directory —
        # the fixtures dir is read-only input and may be the frozen record.
        model_key_safe = model.model_key.replace("/", "_")
        component_dir = self.run_dir / paper / f"benchmark_{model_key_safe}"

        if component_dir.exists() and (component_dir / "calibration.json").exists():
            self.logger.info(f"  Using existing component dir: {component_dir}")
            return component_dir

        self.logger.info(f"  Setting up component dir: {component_dir}")

        device_bw = project_dir / "device_bw.png"
        length_um, width_um = self._get_footprint(paper)

        # Setup component directory
        gds_generation.setup_component_directory(
            component_dir=component_dir,
            device_bw_path=str(device_bw),
            footprint_length_um=length_um,
            footprint_width_um=width_um,
        )

        # Run calibration
        gds_generation.run_calibration(
            component_dir=component_dir,
            michaelangelo_dir=self.config.michaelangelo_dir,
        )

        return component_dir

    def _run_model(self, paper: str, model: BenchmarkModel) -> Dict[str, Any]:
        """Run Phase 1 and Phase 2 for a model on a paper."""
        from homi import gds_generation

        self.logger.info(f"\n--- {model.name} ({model.model_key}) ---")

        # Setup component directory
        component_dir = self._setup_component_dir(paper, model)

        # Create output directory for this model
        model_key_safe = model.model_key.replace("/", "_")
        model_output_dir = self.run_dir / paper / model_key_safe
        model_output_dir.mkdir(parents=True, exist_ok=True)

        # Phase 1
        self.logger.info(f"  Phase 1: {self.config.phase1.num_seeds} seeds, "
                        f"{self.config.phase1.num_parallel} workers")

        # Calculate seed range from num_seeds
        seed_range = self.config.phase1.num_seeds // 2

        phase1_result = gds_generation.run_phase1(
            component_dir=component_dir,
            michaelangelo_dir=self.config.michaelangelo_dir,
            base_seed=self.config.phase1.base_seed,
            seed_range=seed_range,
            num_parallel=self.config.phase1.num_parallel,
            model=model.model_key,
            reasoning_effort=self.config.phase1.reasoning_effort,
        )

        # Copy phase1 results to benchmark output dir
        phase1_summary = component_dir / "phase1" / "exploration_summary.json"
        phase1_telemetry = component_dir / "phase1" / "telemetry_summary.json"
        if phase1_summary.exists():
            import shutil
            dest_dir = model_output_dir / "phase1"
            dest_dir.mkdir(exist_ok=True)
            shutil.copy(phase1_summary, dest_dir / "exploration_summary.json")
            if phase1_telemetry.exists():
                shutil.copy(phase1_telemetry, dest_dir / "telemetry_summary.json")

        # Extract best SSE from ranked results
        ranked = phase1_result.get('ranked_by_sse', [])
        best_sse = ranked[0]['final_sse'] if ranked else phase1_result.get('error', 'N/A')
        self.logger.info(f"  Phase 1 complete - Best SSE: {best_sse}")

        # Phase 2: only on top K seeds by SSE
        self.logger.info(f"  Phase 2: top {self.config.phase2.top_k} seeds, "
                        f"{self.config.phase2.additional_turns} additional turns")

        # Calculate SSE threshold to select top K
        sse_threshold = self._get_sse_threshold_for_top_k(
            component_dir / "phase1" / "exploration_summary.json",
            self.config.phase2.top_k
        )

        phase2_result = gds_generation.run_phase2(
            component_dir=component_dir,
            michaelangelo_dir=self.config.michaelangelo_dir,
            sse_threshold=sse_threshold,
            additional_turns=self.config.phase2.additional_turns,
            num_parallel=self.config.phase2.num_parallel,
            model=model.model_key,
        )

        # Copy phase2 results
        phase2_summary = component_dir / "phase2" / "extended_exploration_summary.json"
        phase2_telemetry = component_dir / "phase2" / "telemetry_summary.json"
        if phase2_summary.exists():
            import shutil
            dest_dir = model_output_dir / "phase2"
            dest_dir.mkdir(exist_ok=True)
            shutil.copy(phase2_summary, dest_dir / "extended_exploration_summary.json")
            if phase2_telemetry.exists():
                shutil.copy(phase2_telemetry, dest_dir / "telemetry_summary.json")

        self.logger.info(f"  Phase 2 complete - Best SSE: {phase2_result.get('best_final_sse', 'N/A')}")

        # Create model summary
        summary = {
            "model": model.name,
            "model_key": model.model_key,
            "family": model.family,
            "paper": paper,
            "phase1": phase1_result,
            "phase2": phase2_result,
            "best_sse": phase2_result.get("best_final_sse", phase1_result.get("best_sse")),
            "best_iou": phase2_result.get("best_final_iou", phase1_result.get("best_iou")),
            "success": True,
        }

        # Save model summary
        with open(model_output_dir / "model_summary.json", "w") as f:
            json.dump(summary, f, indent=2)

        return summary

    def _get_sse_threshold_for_top_k(self, summary_path: Path, top_k: int) -> float:
        """Get SSE threshold that selects top K seeds."""
        if not summary_path.exists():
            return float('inf')

        with open(summary_path) as f:
            summary = json.load(f)

        ranked = summary.get("ranked_by_sse", [])
        if len(ranked) <= top_k:
            return float('inf')  # All seeds qualify

        # Get SSE of the Kth seed (0-indexed)
        kth_sse = ranked[top_k - 1].get("final_sse", float('inf'))

        # Add small buffer to ensure we get exactly K
        return kth_sse + 1.0

    def _is_model_complete(self, paper: str, model: BenchmarkModel) -> bool:
        """Check if model benchmark already completed."""
        model_key_safe = model.model_key.replace("/", "_")
        summary_path = self.run_dir / paper / model_key_safe / "model_summary.json"
        return summary_path.exists()

    def _load_model_results(self, paper: str, model: BenchmarkModel) -> Dict[str, Any]:
        """Load existing model results."""
        model_key_safe = model.model_key.replace("/", "_")
        summary_path = self.run_dir / paper / model_key_safe / "model_summary.json"

        with open(summary_path) as f:
            return json.load(f)
