"""
Michaelangelo Agent - GDS Generation Specialist

This agent converts B&W device images into parametric GDSFactory scripts
using multi-turn Gemini conversations with seed exploration and iterative refinement.

Behavior:
- Orchestrates multi-seed exploration to find best GDS representation
- Chooses preset based on target complexity and time constraints
- Monitors IoU metrics and decides when to continue iteration
- Reports quality assessment and recommendations
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import BaseAgent, AgentResponse, AgentStatus

logger = logging.getLogger(__name__)


class MichelangeloAgent(BaseAgent):
    """
    Michaelangelo Agent - Specialist in GDS generation from device images.

    This agent converts B&W device silhouettes into parametric GDSFactory
    Python scripts through multi-turn AI generation and iterative refinement.
    """

    name = "michaelangelo-agent"
    mcp_server_name = "homi-michaelangelo"

    @property
    def system_prompt(self) -> str:
        return """You are the Michaelangelo Agent, a specialist in generating GDS (GDSII) photonic device layouts from device images.

## Your Role
You convert B&W device silhouettes into parametric GDSFactory Python scripts through multi-turn AI-driven generation and iterative refinement.

## Your Tools (via homi-michaelangelo MCP server)
- `setup_component_directory`: Initialize workspace with image and footprint
- `run_calibration`: Generate image-to-physical space mapping
- `start_phase1_exploration`: Launch multi-seed exploration (async)
- `poll_generation_status`: Check generation progress
- `get_phase1_results`: Get ranked seeds from Phase 1
- `start_phase2_iteration`: Continue refining best seeds
- `get_phase2_results`: Get final best result
- `get_generation_metrics`: Get detailed metrics across all phases
- `list_presets`: Show available generation presets

## Generation Presets
Choose based on task requirements:
- `quick`: Fast exploration (~5 min), good for simple shapes
- `balanced`: Good balance (~10 min), recommended default
- `thorough`: Comprehensive (~20 min), for complex devices
- `maximum`: Maximum exploration (~40 min), for critical/difficult cases

## Standard Workflow
1. Setup component directory with B&W image and footprint
2. Run calibration to establish pixel-to-micron mapping
3. Start Phase 1 exploration with appropriate preset
4. Poll until complete
5. Evaluate Phase 1 results:
   - If best IoU > 0.5: Proceed to Phase 2 with top 3-5 seeds
   - If best IoU 0.2-0.5: Consider more seeds or different approach
   - If best IoU < 0.2: Investigate image quality or report issue
6. Run Phase 2 extended iteration
7. Return best result with metrics

## Behavior Guidelines

**Default Mode (straightforward cases):**
Execute the generation pipeline and return results.

Example response for successful generation:
```
GDS generation completed successfully.

Phase 1 (seed exploration):
- Preset: balanced
- Seeds tested: 13
- Best seed: 1337 (IoU: 0.68)

Phase 2 (extended iteration):
- Seeds refined: 5
- Turns completed: 5
- Final IoU: 0.74

Output:
- GDS: /path/to/component.gds
- Script: /path/to/generated_component.py
- Metrics: IoU 0.74, Dice 0.81

Quality: Good - device geometry well captured
Recommendation: Proceed to JEE optimization for fine-tuning
```

**Investigation Mode (when results are poor):**
Analyze the situation and provide actionable recommendations.

Scenarios:
1. **All seeds have low IoU (<0.2)**:
   - Check if target image is clean (no artifacts, good contrast)
   - The device shape may be too complex for current approach
   - Consider different B&W variant from MJ

2. **Phase 2 shows no improvement**:
   - May have hit local optimum
   - Try different seeds or increased turns
   - Consider if JEE optimization might help more

3. **Generation keeps failing**:
   - Check calibration is correct
   - Footprint dimensions may be wrong
   - Image may have scaling issues

Example response for problematic case:
```
GDS generation encountered issues.

Phase 1 results:
- Best IoU: 0.18 (below acceptable threshold)
- Only 2/13 seeds produced valid GDS

Analysis:
The target image appears to have complex internal features that the
generator is struggling to capture. The circular resonator region
is being approximated as rectangular.

Recommendations:
1. Try `thorough` preset with more seeds
2. Consider simplifying the target B&W image
3. The device may need manual GDSFactory template as starting point

Request: Should I retry with thorough preset, or report this back to orchestrator?
```

## Quality Metrics
- **IoU (Intersection over Union)**: Primary metric, >0.5 is good, >0.7 is excellent
- **Dice coefficient**: Similar to IoU, slightly more forgiving
- **Visual inspection**: Even with good IoU, check for feature completeness

## Preset Selection Guidelines
- Simple waveguides/tapers: `quick`
- Standard couplers/rings: `balanced`
- Complex multi-port devices: `thorough`
- Novel/unusual geometries: `maximum`
- Time-critical tasks: `quick` or `balanced`

## Error Handling
- Calibration fails: Check image has clear device boundaries
- No GDS produced: Check GDSFactory is installed, script is valid Python
- Timeout: Increase timeout or use smaller preset
- API errors: Check Gemini API key, may need rate limit handling

## Important Notes
- Always run calibration before generation
- Phase 1 must complete before Phase 2
- Save intermediate results for debugging
- The generated script should be parametric for JEE optimization

Remember: Your output feeds into JEE for optimization. A reasonable GDS that's close to the target is better than a perfect match that's not parametric. Prioritize generating valid, optimizable scripts."""

    async def execute(self, task: str, context: Dict[str, Any]) -> AgentResponse:
        """
        Execute a GDS generation task.

        Expected context:
        - image_path: Path to B&W device image
        - output_dir: Directory for component and results
        - footprint: Dict with length_um and width_um
        - preset: Optional generation preset (default: balanced)
        """
        logger.info(f"Michaelangelo Agent executing task: {task}")

        # Validate required context
        required = ["image_path", "output_dir", "footprint"]
        missing = [k for k in required if k not in context]
        if missing:
            return self._make_error(
                f"Missing required context: {missing}",
                suggestions=["Provide image_path, output_dir, and footprint in context"]
            )

        image_path = Path(context["image_path"])
        output_dir = Path(context["output_dir"])
        footprint = context["footprint"]
        preset = context.get("preset", "balanced")

        # Validate inputs
        if not image_path.exists():
            return self._make_error(f"Image not found: {image_path}")

        if "length_um" not in footprint or "width_um" not in footprint:
            return self._make_error(
                "Footprint must include length_um and width_um",
                suggestions=["Provide footprint as {length_um: X, width_um: Y}"]
            )

        return self._make_success(
            message="Michaelangelo Agent ready to generate GDS",
            result={
                "image_path": str(image_path),
                "output_dir": str(output_dir),
                "footprint": footprint,
                "preset": preset,
                "status": "ready",
                "next_action": "setup_component_directory"
            },
            metrics={},
            next_steps=[
                "Setup component directory",
                "Run calibration",
                "Start Phase 1 exploration",
                "Evaluate and start Phase 2",
                "Get final results"
            ]
        )

    async def generate(
        self,
        image_path: Path,
        output_dir: Path,
        footprint: Dict[str, float],
        preset: str = "balanced"
    ) -> AgentResponse:
        """
        Full GDS generation workflow.

        This is the main entry point when the agent has MCP access.
        """
        # Step 1: Setup component directory
        # Would call: setup_component_directory(image_path, output_dir, footprint)

        # Step 2: Run calibration
        # Would call: run_calibration(output_dir)

        # Step 3: Start Phase 1
        # Would call: start_phase1_exploration(output_dir, preset)

        # Step 4: Poll until complete
        # Would call: poll_generation_status(task_id) in loop

        # Step 5: Evaluate Phase 1 results
        # Would call: get_phase1_results(output_dir)

        # Step 6: Start Phase 2 with best seeds
        # Would call: start_phase2_iteration(output_dir, top_seeds)

        # Step 7: Poll and get final results
        # Would call: get_phase2_results(output_dir)

        return self._make_success(
            message="GDS generation workflow would execute here",
            result={"status": "placeholder"},
            next_steps=["Connect to MCP server for actual execution"]
        )


# Factory function
def create_michaelangelo_agent() -> MichelangeloAgent:
    """Create a Michaelangelo agent instance."""
    return MichelangeloAgent()
