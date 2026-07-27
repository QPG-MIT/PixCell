"""
JEE Agent - GDS Parameter Optimization Specialist

This agent handles numerical optimization of parametric GDS designs
to match target images. It uses Powell/Nelder-Mead optimization to
minimize the Sum of Squared Errors (SSE) between generated and target layouts.

Behavior:
- Usually just executes optimization and returns results
- Investigates when optimization fails to converge
- Suggests parameter bound adjustments when stuck
- Reports which parameters had most impact
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import BaseAgent, AgentResponse, AgentStatus

logger = logging.getLogger(__name__)


class JEEAgent(BaseAgent):
    """
    JEE Agent - Specialist in GDS parameter optimization.

    This agent fine-tunes parametric GDSFactory scripts to match
    target device images using numerical optimization.
    """

    name = "jee-agent"
    mcp_server_name = "homi-jee"

    @property
    def system_prompt(self) -> str:
        return """You are the JEE Agent, a specialist in numerical optimization of GDS (GDSII) photonic device layouts.

## Your Role
You fine-tune parametric GDSFactory Python scripts to match target device images by minimizing the Sum of Squared Errors (SSE) between generated and target layouts.

## Your Tools (via homi-jee MCP server)
- `extract_parameters`: Parse a GDSFactory script to find tunable numeric parameters
- `compute_sse`: Calculate SSE and related metrics between target and generated images
- `run_optimization`: Start Powell/Nelder-Mead optimization (async, returns task_id)
- `poll_optimization`: Check optimization progress
- `get_optimization_result`: Get final results when complete
- `apply_parameters`: Apply optimized parameters to generate new GDS

## Standard Workflow
1. Extract parameters from the input script
2. Compute baseline SSE to understand starting point
3. Run optimization with appropriate bounds
4. Poll until complete
5. Report results with improvement percentage

## Behavior Guidelines

**Default Mode (95% of cases):**
Just execute the optimization and return results. Don't over-think simple cases.

Example response for successful optimization:
```
Optimization completed successfully.
- Baseline SSE: 89,854
- Final SSE: 32,304 (64% improvement)
- Iterations: 187
- Best parameters: {length: 12.5, width: 0.42, gap: 0.08}
- Output: /path/to/best_component.gds
```

**Investigation Mode (when things go wrong):**
If optimization fails or shows poor improvement, investigate:

1. **Convergence failure**: Try different initial conditions or wider bounds
2. **Parameter hitting bounds**: The search space may be too constrained
3. **No improvement**: The target image may have features outside parameter space
4. **Oscillating SSE**: Reduce step size or try different method

Example response for problematic optimization:
```
Optimization partially succeeded but encountered issues.
- Baseline SSE: 89,854
- Final SSE: 78,234 (only 13% improvement)
- Issue: Parameter 'taper_length' repeatedly hit upper bound (20.0)

Recommendation: Expand taper_length bounds to [5, 40] and re-run.
Alternatively, the target shape may require a different component type.
```

## What NOT to do
- Don't run optimization without understanding the parameter space
- Don't accept poor results without investigating
- Don't suggest re-running Michaelangelo unless optimization truly can't help
- Don't over-engineer simple parameter tuning tasks

## Metrics to Report
- Baseline SSE (starting point)
- Final SSE (after optimization)
- Improvement percentage
- Number of iterations
- Whether result is within footprint constraints
- Which parameters changed most (sensitivity insight)

## Error Handling
If a tool call fails:
1. Check if paths are valid
2. Check if calibration file exists
3. Check if script is valid Python/GDSFactory
4. Report specific error with actionable suggestion

Remember: You are an optimization specialist. Your job is to find the best parameters, not to generate new designs. If the design fundamentally can't match the target, report that clearly so the orchestrator can re-route to Michaelangelo."""

    async def execute(self, task: str, context: Dict[str, Any]) -> AgentResponse:
        """
        Execute an optimization task.

        Expected context:
        - script_path: Path to GDSFactory script
        - target_image: Path to target image
        - calibration_file: Path to calibration.json
        - output_dir: Directory for outputs
        - param_bounds: Optional dict of parameter bounds
        """
        logger.info(f"JEE Agent executing task: {task}")

        # Validate required context
        required = ["script_path", "target_image", "calibration_file", "output_dir"]
        missing = [k for k in required if k not in context]
        if missing:
            return self._make_error(
                f"Missing required context: {missing}",
                suggestions=["Provide all required paths in context"]
            )

        script_path = Path(context["script_path"])
        target_image = Path(context["target_image"])
        calibration_file = Path(context["calibration_file"])
        output_dir = Path(context["output_dir"])

        # Validate paths exist
        if not script_path.exists():
            return self._make_error(f"Script not found: {script_path}")
        if not target_image.exists():
            return self._make_error(f"Target image not found: {target_image}")
        if not calibration_file.exists():
            return self._make_error(f"Calibration file not found: {calibration_file}")

        # This would be filled in when connected to actual MCP client
        # For now, return a structured response showing what would happen
        return self._make_success(
            message="JEE Agent ready to optimize",
            result={
                "script_path": str(script_path),
                "target_image": str(target_image),
                "calibration_file": str(calibration_file),
                "output_dir": str(output_dir),
                "status": "ready",
                "next_action": "run_optimization"
            },
            metrics={},
            next_steps=[
                "Extract parameters from script",
                "Compute baseline SSE",
                "Run optimization",
                "Apply best parameters"
            ]
        )

    async def optimize(
        self,
        script_path: Path,
        target_image: Path,
        calibration_file: Path,
        output_dir: Path,
        param_bounds: Optional[Dict[str, List[float]]] = None,
        max_iterations: int = 150
    ) -> AgentResponse:
        """
        Run full optimization workflow.

        This is the main entry point when the agent has MCP access.
        """
        # Step 1: Extract parameters if bounds not provided
        if param_bounds is None:
            # Would call: extract_parameters(script_path)
            # For now, placeholder
            return self._make_needs_input(
                "No parameter bounds provided. Please specify which parameters to optimize and their bounds.",
                options=[
                    "Extract parameters automatically from script",
                    "Provide param_bounds dict manually"
                ]
            )

        # Step 2: Compute baseline SSE
        # Would call: compute_sse(target_image, initial_raster)

        # Step 3: Run optimization
        # Would call: run_optimization(...)

        # Step 4: Poll until complete
        # Would call: poll_optimization(task_id) in loop

        # Step 5: Get and report results
        # Would call: get_optimization_result(task_id)

        # Placeholder response
        return self._make_success(
            message="Optimization workflow would execute here",
            result={"status": "placeholder"},
            next_steps=["Connect to MCP server for actual execution"]
        )


# Factory function for creating agent
def create_jee_agent() -> JEEAgent:
    """Create a JEE agent instance."""
    return JEEAgent()
