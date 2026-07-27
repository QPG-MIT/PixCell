"""
HOMI Orchestrator Agent

The main agent that coordinates all sub-agents to execute the
paper-to-simulation pipeline. Delegates to specialist agents
and makes high-level decisions about pipeline flow.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .pipeline import (
    Pipeline,
    PipelineConfig,
    PipelineStage,
    PipelineResult,
    StageResult,
    STANDARD_PIPELINE,
    FULL_PIPELINE,
    QUICK_PIPELINE,
    SIMULATION_PIPELINE,
)

logger = logging.getLogger(__name__)


# Orchestrator system prompt
ORCHESTRATOR_SYSTEM_PROMPT = """You are the HOMI Orchestrator, responsible for coordinating a multi-agent system that converts silicon photonics research papers into fabrication-ready GDS designs.

## Your Role
You coordinate specialist agents to execute a paper-to-simulation pipeline:
1. **MJ Agent**: Extract device images from papers
2. **Michaelangelo Agent**: Generate GDS from images
3. **JEE Agent**: Optimize GDS parameters
4. **Weber Agent**: Create interactive explorers
5. **PDK Agent**: Map to foundry processes
6. **Flex Agent**: FDTD simulation via Tidy3D

## Your Responsibilities
- Decide which stages to run based on user requirements
- Pass context between stages
- Handle errors and decide on retries or alternatives
- Make high-level decisions when agents report uncertainty
- Track overall progress and quality metrics
- Report final results to the user

## Pipeline Flows
- **Quick**: MJ → Michaelangelo (fast, basic GDS)
- **Standard**: MJ → Michaelangelo → JEE → Weber (recommended)
- **Full**: Standard + PDK → Simulation (production-ready)
- **Simulation**: Standard + Simulation (quick simulation via Tidy3D)

## Decision Guidelines

**When to Proceed:**
- Agent reports success with good metrics
- Optional stage fails but results are usable

**When to Retry:**
- Agent reports transient error (API timeout, etc.)
- Metrics are borderline and retry might help

**When to Seek Guidance:**
- Agent explicitly requests input
- Multiple equally valid paths exist
- Quality metrics are consistently poor

**When to Stop:**
- Required stage fails and can't be recovered
- User cancels
- Critical error (missing files, invalid input)

## Metrics to Track
- MJ: Image selection confidence (>7 is good)
- Michaelangelo: IoU (>0.5 is good, >0.7 is excellent)
- JEE: SSE improvement percentage (>30% is good)
- Weber: Parameters extracted, components detected
- PDK: DRC pass/fail, violation count

## Communication Style
- Report progress at each stage
- Explain decisions when not obvious
- Provide clear next steps
- Summarize final results with paths and metrics
"""


class Orchestrator:
    """
    Main orchestrator that coordinates the HOMI multi-agent pipeline.
    """

    def __init__(self, config: PipelineConfig = None):
        self.config = config or PipelineConfig()
        self.pipeline = Pipeline(self.config)
        self.start_time: Optional[datetime] = None

    @property
    def system_prompt(self) -> str:
        return ORCHESTRATOR_SYSTEM_PROMPT

    async def run(
        self,
        pdf_path: str,
        output_dir: Optional[str] = None,
        footprint: Optional[Dict[str, float]] = None,
        pipeline_type: str = "standard"
    ) -> PipelineResult:
        """
        Run the full pipeline on a paper.

        Args:
            pdf_path: Path to the research paper PDF
            output_dir: Directory for all outputs (default: auto-generated)
            footprint: Optional device footprint {length_um, width_um}
            pipeline_type: "quick", "standard", or "full"

        Returns:
            PipelineResult with all stage results and final outputs
        """
        self.start_time = datetime.now()
        logger.info(f"Starting {pipeline_type} pipeline for {pdf_path}")

        # Setup output directory
        pdf_path = Path(pdf_path)
        if output_dir is None:
            output_dir = pdf_path.parent / "outputs" / pdf_path.stem
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Configure pipeline based on type
        if pipeline_type == "quick":
            stages = QUICK_PIPELINE
        elif pipeline_type == "full":
            stages = FULL_PIPELINE
        elif pipeline_type == "simulation":
            stages = SIMULATION_PIPELINE
        else:
            stages = STANDARD_PIPELINE

        # Disable stages not in selected pipeline
        for stage in PipelineStage:
            self.config.stages[stage].enabled = stage in stages

        # Initialize context
        self.pipeline.context = {
            "pdf_path": str(pdf_path),
            "output_dir": str(output_dir),
            "footprint": footprint,
        }

        # Execute pipeline
        for stage in self.pipeline.get_enabled_stages():
            logger.info(f"Executing stage: {stage.value}")

            try:
                result = await self._execute_stage(stage)
                self.pipeline.record_result(result)

                if not self.pipeline.can_continue():
                    logger.error(f"Pipeline stopped at {stage.value}: {result.error}")
                    break

            except Exception as e:
                logger.error(f"Exception in stage {stage.value}: {e}")
                self.pipeline.record_result(StageResult(
                    stage=stage,
                    success=False,
                    message=f"Exception: {e}",
                    error=str(e)
                ))
                if self.config.stages[stage].required:
                    break

        # Calculate total time
        end_time = datetime.now()
        total_time = (end_time - self.start_time).total_seconds()

        # Get summary
        result = self.pipeline.get_summary()
        result.total_time_seconds = total_time

        logger.info(f"Pipeline completed in {total_time:.1f}s: {result.message}")
        return result

    async def _execute_stage(self, stage: PipelineStage) -> StageResult:
        """Execute a single pipeline stage."""
        handlers = {
            PipelineStage.MJ: self._run_mj,
            PipelineStage.MICHAELANGELO: self._run_michaelangelo,
            PipelineStage.JEE: self._run_jee,
            PipelineStage.WEBER: self._run_weber,
            PipelineStage.PDK: self._run_pdk,
            PipelineStage.SIMULATION: self._run_simulation,
        }

        handler = handlers.get(stage)
        if handler is None:
            return StageResult(
                stage=stage,
                success=False,
                message=f"No handler for stage: {stage}",
                error="Handler not implemented"
            )

        return await handler()

    async def _run_mj(self) -> StageResult:
        """Run MJ agent for paper processing."""
        ctx = self.pipeline.context
        pdf_path = ctx["pdf_path"]
        output_dir = Path(ctx["output_dir"]) / "mj"
        output_dir.mkdir(exist_ok=True)

        # This would call the actual MJ agent
        # For now, simulate the workflow
        logger.info(f"MJ: Processing {pdf_path}")

        # Placeholder result
        return StageResult(
            stage=PipelineStage.MJ,
            success=True,
            message="Paper processing completed",
            outputs={
                "device_image": str(output_dir / "device_bw.png"),
                "selected_image": str(output_dir / "selected_image.png"),
            },
            metrics={
                "images_extracted": 12,
                "best_score": 8.2,
                "variants_generated": 5
            }
        )

    async def _run_michaelangelo(self) -> StageResult:
        """Run Michaelangelo agent for GDS generation."""
        ctx = self.pipeline.context
        device_image = ctx.get("device_image")
        footprint = ctx.get("footprint", {"length_um": 40, "width_um": 10})
        output_dir = Path(ctx["output_dir"]) / "michaelangelo"
        output_dir.mkdir(exist_ok=True)

        if not device_image:
            return StageResult(
                stage=PipelineStage.MICHAELANGELO,
                success=False,
                message="No device image from MJ stage",
                error="Missing device_image in context"
            )

        logger.info(f"Michaelangelo: Generating GDS from {device_image}")

        # Placeholder result
        return StageResult(
            stage=PipelineStage.MICHAELANGELO,
            success=True,
            message="GDS generation completed",
            outputs={
                "gds_path": str(output_dir / "component.gds"),
                "script_path": str(output_dir / "generated_component.py"),
                "component_dir": str(output_dir),
            },
            metrics={
                "best_iou": 0.72,
                "best_seed": 1337,
                "turns_completed": 5
            }
        )

    async def _run_jee(self) -> StageResult:
        """Run JEE agent for optimization."""
        ctx = self.pipeline.context
        script_path = ctx.get("script_path")
        device_image = ctx.get("device_image")
        component_dir = ctx.get("component_dir")
        output_dir = Path(ctx["output_dir"]) / "jee"
        output_dir.mkdir(exist_ok=True)

        if not script_path:
            return StageResult(
                stage=PipelineStage.JEE,
                success=False,
                message="No script from Michaelangelo stage",
                error="Missing script_path in context"
            )

        logger.info(f"JEE: Optimizing {script_path}")

        # Placeholder result
        return StageResult(
            stage=PipelineStage.JEE,
            success=True,
            message="Optimization completed",
            outputs={
                "optimized_gds": str(output_dir / "optimized.gds"),
                "optimized_script": str(output_dir / "optimized_component.py"),
                "best_params": {"length": 42.5, "width": 0.45, "gap": 0.15},
            },
            metrics={
                "baseline_sse": 89854,
                "final_sse": 32304,
                "improvement_pct": 64.0,
                "iterations": 187
            }
        )

    async def _run_weber(self) -> StageResult:
        """Run Weber agent for explorer generation."""
        ctx = self.pipeline.context
        script_path = ctx.get("optimized_script") or ctx.get("script_path")
        output_dir = Path(ctx["output_dir"]) / "weber"
        output_dir.mkdir(exist_ok=True)

        if not script_path:
            return StageResult(
                stage=PipelineStage.WEBER,
                success=False,
                message="No script to analyze",
                error="Missing script_path in context"
            )

        logger.info(f"Weber: Generating explorer from {script_path}")

        # Placeholder result
        return StageResult(
            stage=PipelineStage.WEBER,
            success=True,
            message="Explorer generated",
            outputs={
                "explorer_dir": str(output_dir),
                "app_path": str(output_dir / "app.py"),
            },
            metrics={
                "parameters_extracted": 8,
                "components_detected": 5,
                "swappable_groups": 2
            }
        )

    async def _run_pdk(self) -> StageResult:
        """Run PDK agent for foundry mapping."""
        ctx = self.pipeline.context
        gds_path = ctx.get("optimized_gds") or ctx.get("gds_path")
        pdf_path = ctx.get("pdf_path")
        output_dir = Path(ctx["output_dir"]) / "pdk"
        output_dir.mkdir(exist_ok=True)

        if not gds_path:
            return StageResult(
                stage=PipelineStage.PDK,
                success=False,
                message="No GDS to convert",
                error="Missing gds_path in context"
            )

        logger.info(f"PDK: Mapping {gds_path} to foundry PDK")

        # Placeholder result
        return StageResult(
            stage=PipelineStage.PDK,
            success=True,
            message="PDK mapping completed",
            outputs={
                "pdk_gds": str(output_dir / "design_aim.gds"),
                "target_pdk": "aim_photonics",
            },
            metrics={
                "match_confidence": 80,
                "drc_passed": True,
                "violations": 0
            }
        )

    async def _run_simulation(self) -> StageResult:
        """Run Flex agent for Tidy3D FDTD simulation."""
        ctx = self.pipeline.context
        gds_path = ctx.get("pdk_gds") or ctx.get("optimized_gds") or ctx.get("gds_path")
        api_key = ctx.get("tidy3d_api_key")
        output_dir = Path(ctx["output_dir"]) / "simulation"
        output_dir.mkdir(exist_ok=True)

        if not gds_path:
            return StageResult(
                stage=PipelineStage.SIMULATION,
                success=False,
                message="No GDS file for simulation",
                error="Missing gds_path in context"
            )

        logger.info(f"Simulation: Configuring Tidy3D simulation for {gds_path}")

        # This would call the actual Flex agent via MCP
        # The workflow:
        # 1. is_tidy3d_available() - check dependencies
        # 2. validate_api_key(api_key) - verify credentials
        # 3. get_simulation_info(gds_path, config) - preview simulation
        # 4. create_and_upload_simulation(gds_path, api_key, config) - upload
        # 5. get_task_status(task_id) - poll status
        # 6. get_workbench_url(task_id) - return visualization link

        # Get simulation config from context or use defaults
        sim_config = ctx.get("simulation_config", {})
        material = sim_config.get("material", "Silicon (SOI)")
        thickness_nm = sim_config.get("thickness_nm", 220)
        wavelength_um = sim_config.get("wavelength_um", 1.55)

        # Placeholder result
        return StageResult(
            stage=PipelineStage.SIMULATION,
            success=True,
            message="Simulation created and uploaded to Tidy3D",
            outputs={
                "task_id": "tsk_placeholder_123",
                "workbench_url": "https://tidy3d.simulation.cloud/workbench?taskId=tsk_placeholder_123",
                "simulation_config": {
                    "material": material,
                    "thickness_nm": thickness_nm,
                    "wavelength_um": wavelength_um,
                }
            },
            metrics={
                "tidy3d_available": True,
                "api_key_valid": bool(api_key),
                "domain_size_um3": "25.5 × 12.3 × 2.44",
                "grid_resolution": "12 points/wavelength",
                "estimated_cost_flexcredits": 2.5,
            }
        )

    def get_progress_summary(self) -> str:
        """Get a human-readable progress summary."""
        lines = ["HOMI Pipeline Progress", "=" * 40]

        for stage in FULL_PIPELINE:
            if stage in self.pipeline.results:
                result = self.pipeline.results[stage]
                status = "SUCCESS" if result.success else "FAILED"
                lines.append(f"{stage.value}: {status} - {result.message}")
            elif self.config.stages[stage].enabled:
                if self.pipeline.current_stage == stage:
                    lines.append(f"{stage.value}: RUNNING...")
                else:
                    lines.append(f"{stage.value}: PENDING")
            else:
                lines.append(f"{stage.value}: SKIPPED")

        return "\n".join(lines)


# CLI entry point
async def main():
    """CLI entry point for running the orchestrator."""
    import argparse

    parser = argparse.ArgumentParser(description="HOMI Orchestrator - Paper to GDS Pipeline")
    parser.add_argument("pdf_path", help="Path to research paper PDF")
    parser.add_argument("-o", "--output", help="Output directory")
    parser.add_argument("-p", "--pipeline",
                       choices=["quick", "standard", "full", "simulation"],
                       default="standard", help="Pipeline type")
    parser.add_argument("--length", type=float, help="Device length in um")
    parser.add_argument("--width", type=float, help="Device width in um")
    parser.add_argument("--tidy3d-key", help="Tidy3D API key for simulation")

    args = parser.parse_args()

    # Configure
    config = PipelineConfig()

    footprint = None
    if args.length and args.width:
        footprint = {"length_um": args.length, "width_um": args.width}

    # Run
    orchestrator = Orchestrator(config)

    # Add API key to context if provided
    if args.tidy3d_key:
        orchestrator.pipeline.context["tidy3d_api_key"] = args.tidy3d_key

    result = await orchestrator.run(
        pdf_path=args.pdf_path,
        output_dir=args.output,
        footprint=footprint,
        pipeline_type=args.pipeline
    )

    # Print summary
    print("\n" + orchestrator.get_progress_summary())
    print(f"\nTotal time: {result.total_time_seconds:.1f}s")

    if result.success:
        print("\nFinal outputs:")
        for key, value in result.final_outputs.items():
            print(f"  {key}: {value}")
    else:
        print("\nPipeline failed. Check logs for details.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
