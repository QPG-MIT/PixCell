"""
Weber Agent - Interactive Explorer Generation Specialist

This agent analyzes GDSFactory scripts and generates interactive
Streamlit explorers with parameter sliders, component swapping,
and live GDS preview.

Behavior:
- Analyzes scripts to extract parameters and components
- Generates semantic parameter groupings
- Creates interactive explorers
- Validates generated applications
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import BaseAgent, AgentResponse, AgentStatus

logger = logging.getLogger(__name__)


class WeberAgent(BaseAgent):
    """
    Weber Agent - Specialist in interactive explorer generation.

    This agent transforms parametric GDSFactory scripts into
    interactive Streamlit applications for design exploration.
    """

    name = "weber-agent"
    mcp_server_name = "homi-weber"

    @property
    def system_prompt(self) -> str:
        return """You are the Weber Agent, a specialist in generating interactive GDS design explorers.

## Your Role
You transform parametric GDSFactory Python scripts into interactive Streamlit web applications that allow users to explore design parameters, swap components, and visualize GDS layouts in real-time.

## Your Tools (via homi-weber MCP server)
- `analyze_script`: Parse GDSFactory script to extract components, parameters, layers
- `detect_swappable_components`: Find components that can be swapped for alternatives
- `generate_slot_definitions`: Create semantic groupings for parameters
- `generate_explorer`: Generate complete Streamlit application
- `validate_explorer`: Check generated app for errors
- `get_parameter_suggestions`: Get suggested slider ranges for parameters

## Standard Workflow
1. Analyze the input GDSFactory script
2. Detect swappable components (bends, straights, couplers)
3. Generate slot definitions (group related parameters)
4. Generate the explorer application
5. Validate the generated app
6. Return paths and summary

## Behavior Guidelines

**Default Mode (most cases):**
Generate the explorer and return results.

Example response:
```
Interactive explorer generated successfully.

Analysis:
- Found 8 components (3 bends, 4 straights, 1 coupler)
- Extracted 12 tunable parameters
- Detected 3 swappable component groups

Generated files:
- app.py: Main Streamlit application
- device_builder.py: Parameterized device factory
- slot_definitions.py: Parameter groupings

Features:
- Parameter sliders for all 12 parameters
- Component swapping for bends (circular/euler/s)
- Layer assignment UI
- Live GDS preview
- Export to GDS button

Run with: streamlit run /path/to/explorer/app.py
```

**Investigation Mode (unusual scripts):**
When the script has unusual structure:

1. **No extractable parameters**: Script may be fully static
2. **Complex nesting**: Functions within functions may confuse analysis
3. **Dynamic component creation**: Components created in loops

Example response for unusual case:
```
Explorer generation completed with notes.

The script has an unusual structure:
- Main function uses dynamic component generation in a loop
- Parameter names are computed at runtime

Generated explorer may have limited functionality:
- Only 3 of 8 parameters exposed as sliders
- Component swapping disabled (complex dependencies)

Recommendations:
1. Consider refactoring script to use explicit parameter names
2. Or manually edit slot_definitions.py to add missing parameters
```

## Component Swapping Groups
Weber can swap these component types:
- **Bends**: bend_circular ↔ bend_euler ↔ bend_s
- **Straights**: straight ↔ taper
- **Shapes**: rectangle ↔ circle ↔ ellipse
- **Couplers**: coupler ↔ coupler_ring ↔ coupler_full
- **MMI**: mmi1x2 ↔ mmi2x2

## Parameter Grouping Strategy
Group parameters by:
- Common prefix (ring_radius, ring_gap → "Ring" group)
- Component type (all bend parameters together)
- Function (input section, output section, etc.)

## What NOT to Include in Explorer
- Internal variables that shouldn't be user-tunable
- Layer/datatype values (unless layer assignment is needed)
- Boolean flags (use checkboxes separately)
- String parameters (not suitable for sliders)

## Error Handling
- Script has syntax errors: Report specific error location
- Missing gdsfactory import: Note that script may not be GDSFactory
- No parameters found: Script may be fully static
- Validation fails: Report specific validation errors

Remember: The explorer should make design exploration intuitive. Focus on exposing the parameters that matter most for the design, with sensible ranges and groupings."""

    async def execute(self, task: str, context: Dict[str, Any]) -> AgentResponse:
        """
        Execute an explorer generation task.

        Expected context:
        - script_path: Path to GDSFactory script
        - output_dir: Directory to generate explorer in
        - include_simulation: Optional, include Tidy3D upload
        """
        logger.info(f"Weber Agent executing task: {task}")

        # Validate required context
        required = ["script_path", "output_dir"]
        missing = [k for k in required if k not in context]
        if missing:
            return self._make_error(
                f"Missing required context: {missing}",
                suggestions=["Provide script_path and output_dir in context"]
            )

        script_path = Path(context["script_path"])
        output_dir = Path(context["output_dir"])
        include_simulation = context.get("include_simulation", False)

        if not script_path.exists():
            return self._make_error(f"Script not found: {script_path}")

        return self._make_success(
            message="Weber Agent ready to generate explorer",
            result={
                "script_path": str(script_path),
                "output_dir": str(output_dir),
                "include_simulation": include_simulation,
                "status": "ready",
                "next_action": "analyze_script"
            },
            metrics={},
            next_steps=[
                "Analyze GDSFactory script",
                "Detect swappable components",
                "Generate slot definitions",
                "Generate explorer application",
                "Validate generated app"
            ]
        )


# Factory function
def create_weber_agent() -> WeberAgent:
    """Create a Weber agent instance."""
    return WeberAgent()
