"""
Pipeline Definition for HOMI Multi-Agent System

Defines the stages and flow of the paper-to-simulation pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class PipelineStage(str, Enum):
    """Stages in the HOMI pipeline."""
    MJ = "mj"                      # Paper processing, device extraction
    MICHAELANGELO = "michaelangelo"  # GDS generation
    JEE = "jee"                    # Parameter optimization
    WEBER = "weber"                # Interactive explorer
    PDK = "pdk"                    # Foundry mapping
    SIMULATION = "simulation"      # FDTD simulation (Tidy3D)


@dataclass
class StageConfig:
    """Configuration for a pipeline stage."""
    enabled: bool = True
    required: bool = True  # If False, pipeline can continue on failure
    timeout_seconds: int = 3600  # 1 hour default
    retry_count: int = 1
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineConfig:
    """Configuration for the full pipeline."""
    # Stage configurations
    stages: Dict[PipelineStage, StageConfig] = field(default_factory=lambda: {
        PipelineStage.MJ: StageConfig(enabled=True, required=True),
        PipelineStage.MICHAELANGELO: StageConfig(enabled=True, required=True),
        PipelineStage.JEE: StageConfig(enabled=True, required=False),  # Optional optimization
        PipelineStage.WEBER: StageConfig(enabled=True, required=False),  # Optional explorer
        PipelineStage.PDK: StageConfig(enabled=False, required=False),  # Optional PDK mapping
        PipelineStage.SIMULATION: StageConfig(enabled=False, required=False),  # Tidy3D simulation
    })

    # Quality thresholds
    mj_confidence_threshold: float = 7.0  # Min score for auto-selection
    michaelangelo_min_iou: float = 0.2   # Min IoU to proceed
    jee_min_improvement: float = 0.1     # Min improvement to consider success

    # Preset for Michaelangelo
    generation_preset: str = "balanced"

    # Output settings
    output_dir: Optional[str] = None
    project_name: Optional[str] = None


@dataclass
class StageResult:
    """Result from a pipeline stage."""
    stage: PipelineStage
    success: bool
    message: str
    outputs: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    suggestions: List[str] = field(default_factory=list)


@dataclass
class PipelineResult:
    """Result from full pipeline execution."""
    success: bool
    message: str
    stages_completed: List[PipelineStage] = field(default_factory=list)
    stages_skipped: List[PipelineStage] = field(default_factory=list)
    stages_failed: List[PipelineStage] = field(default_factory=list)
    stage_results: Dict[PipelineStage, StageResult] = field(default_factory=dict)
    final_outputs: Dict[str, Any] = field(default_factory=dict)
    total_time_seconds: float = 0.0


# Standard pipeline flows
STANDARD_PIPELINE = [
    PipelineStage.MJ,
    PipelineStage.MICHAELANGELO,
    PipelineStage.JEE,
    PipelineStage.WEBER,
]

FULL_PIPELINE = [
    PipelineStage.MJ,
    PipelineStage.MICHAELANGELO,
    PipelineStage.JEE,
    PipelineStage.WEBER,
    PipelineStage.PDK,
    PipelineStage.SIMULATION,
]

QUICK_PIPELINE = [
    PipelineStage.MJ,
    PipelineStage.MICHAELANGELO,
]

# Pipeline with simulation enabled
SIMULATION_PIPELINE = [
    PipelineStage.MJ,
    PipelineStage.MICHAELANGELO,
    PipelineStage.JEE,
    PipelineStage.WEBER,
    PipelineStage.SIMULATION,
]


class Pipeline:
    """
    Manages pipeline execution state and flow.
    """

    def __init__(self, config: PipelineConfig = None):
        self.config = config or PipelineConfig()
        self.current_stage: Optional[PipelineStage] = None
        self.results: Dict[PipelineStage, StageResult] = {}
        self.context: Dict[str, Any] = {}

    def get_enabled_stages(self) -> List[PipelineStage]:
        """Get list of enabled stages in order."""
        return [
            stage for stage in FULL_PIPELINE
            if self.config.stages[stage].enabled
        ]

    def get_next_stage(self) -> Optional[PipelineStage]:
        """Get the next stage to execute."""
        enabled = self.get_enabled_stages()

        if self.current_stage is None:
            return enabled[0] if enabled else None

        try:
            current_idx = enabled.index(self.current_stage)
            if current_idx + 1 < len(enabled):
                return enabled[current_idx + 1]
        except ValueError:
            pass

        return None

    def record_result(self, result: StageResult):
        """Record a stage result."""
        self.results[result.stage] = result
        self.current_stage = result.stage

        # Update context with outputs
        self.context.update(result.outputs)

    def can_continue(self) -> bool:
        """Check if pipeline can continue after current stage."""
        if self.current_stage is None:
            return True

        result = self.results.get(self.current_stage)
        if result is None:
            return True

        stage_config = self.config.stages[self.current_stage]

        if result.success:
            return True

        # Can continue if stage is not required
        return not stage_config.required

    def get_summary(self) -> PipelineResult:
        """Get summary of pipeline execution."""
        completed = []
        skipped = []
        failed = []

        for stage in FULL_PIPELINE:
            if stage in self.results:
                if self.results[stage].success:
                    completed.append(stage)
                else:
                    failed.append(stage)
            elif not self.config.stages[stage].enabled:
                skipped.append(stage)

        success = len(failed) == 0 or all(
            not self.config.stages[s].required for s in failed
        )

        return PipelineResult(
            success=success,
            message="Pipeline completed" if success else "Pipeline failed",
            stages_completed=completed,
            stages_skipped=skipped,
            stages_failed=failed,
            stage_results=self.results.copy(),
            final_outputs=self.context.copy()
        )
