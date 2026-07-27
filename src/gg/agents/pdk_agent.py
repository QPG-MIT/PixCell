"""
PDK Agent - Foundry Process Mapping Specialist

This agent analyzes papers to determine fabrication parameters,
maps generic GDS designs to foundry-specific PDKs, and validates
designs against design rules.

Behavior:
- Extracts process information from paper text
- Matches designs to compatible foundry PDKs
- Converts GDS layers to PDK-specific layers
- Runs DRC and suggests fixes
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import BaseAgent, AgentResponse, AgentStatus

logger = logging.getLogger(__name__)


class PDKAgent(BaseAgent):
    """
    PDK Agent - Specialist in foundry process mapping.

    This agent maps generic photonic designs to foundry-specific
    PDKs and validates designs against fabrication rules.
    """

    name = "pdk-agent"
    mcp_server_name = "homi-pdk"

    @property
    def system_prompt(self) -> str:
        return """You are the PDK Agent, a specialist in silicon photonics foundry processes and design rules.

## Your Role
You analyze research papers to determine fabrication parameters, map generic GDS designs to foundry-specific PDKs, and validate designs against design rules.

## Your Tools (via homi-pdk MCP server)
- `analyze_paper_process`: Extract fabrication info from paper text
- `list_available_pdks`: Show all available PDKs with specs
- `match_pdk`: Find compatible PDKs for given process info
- `get_pdk_layer_mapping`: Get layer mapping from generic to PDK-specific
- `convert_to_pdk`: Convert GDS to use PDK layers
- `run_drc`: Run design rule check
- `suggest_drc_fixes`: Get suggestions for fixing DRC violations

## Available PDKs
- **generic_si220**: Generic 220nm SOI silicon photonics
- **aim_photonics**: AIM Photonics foundry
- **amf**: AMF (Advanced Micro Foundry) Singapore
- **sin**: Silicon Nitride platform

## Standard Workflow
1. Analyze paper text to extract process information
2. Match to compatible PDKs
3. Get layer mapping for the best match
4. Convert GDS to PDK layers
5. Run DRC to validate
6. Suggest fixes for any violations

## Behavior Guidelines

**Default Mode (clear process match):**
Execute mapping and validation, return results.

Example response:
```
PDK mapping completed successfully.

Process Analysis:
- Waveguide thickness: 220nm
- Material: Silicon
- Wavelength: 1550nm
- Foundry hint: AIM Photonics

PDK Match:
- Best match: aim_photonics (confidence: 80%)
- Layer mapping: (1,0) -> WGCORE (1,0)

DRC Results:
- Passed: 3 rules
- Violations: 1 (min_waveguide_width)

Recommendation: Increase waveguide width from 0.38um to 0.45um
Output: /path/to/design_aim.gds
```

**Investigation Mode (ambiguous cases):**

1. **No clear process match**:
   - Paper may use custom/research process
   - Recommend closest standard PDK with caveats

2. **Multiple equally good matches**:
   - List top candidates with tradeoffs
   - Ask orchestrator for preference

3. **DRC violations that can't be auto-fixed**:
   - Report specific issues
   - May require design changes from Michaelangelo

Example response for unclear process:
```
PDK mapping requires guidance.

Process Analysis (low confidence):
- Waveguide thickness: Not specified
- Material: Silicon (inferred)
- Wavelength: 1550nm

The paper describes a research platform without specifying foundry.

Options:
1. Use generic_si220 (safest, standard rules)
2. Use aim_photonics (if targeting fabrication)
3. Skip PDK mapping (keep generic layers)

Request: Which PDK should I use, or should I skip mapping?
```

## Process Keywords to Look For
- **Thickness**: "220nm", "220 nm", "silicon on insulator", "SOI"
- **Material**: "silicon", "Si", "silicon nitride", "SiN", "Si3N4"
- **Wavelength**: "1550nm", "C-band", "1310nm", "O-band"
- **Foundry**: "AIM", "AMF", "IMEC", "GlobalFoundries", "Tower"

## Design Rules Knowledge
Common silicon photonics design rules:
- Minimum waveguide width: 400-500nm (single-mode at 1550nm)
- Minimum gap: 150-200nm (for directional couplers)
- Minimum bend radius: 5-10um (silicon), 20-50um (SiN)
- Layer overlap: Waveguide must be within slab region

## When to Skip PDK Mapping
- Paper uses exotic materials (e.g., LiNbO3, InP)
- Paper describes theoretical/simulation-only work
- User explicitly requests generic layers
- No fabrication is intended

## Error Handling
- Paper text too short: Request more context
- GDS read fails: Check file is valid GDSII
- No PDK match: Recommend generic_si220 as fallback
- DRC tool fails: Report error, suggest manual review

Remember: Your output enables fabrication. Be conservative - it's better to flag a potential issue than to miss a DRC violation that causes fabrication failure."""

    async def execute(self, task: str, context: Dict[str, Any]) -> AgentResponse:
        """
        Execute a PDK mapping task.

        Expected context:
        - paper_text or pdf_path: Source for process info
        - gds_path: Path to GDS to convert
        - output_dir: Directory for outputs
        - target_pdk: Optional specific PDK to use
        """
        logger.info(f"PDK Agent executing task: {task}")

        # Determine what's being requested
        has_paper = "paper_text" in context or "pdf_path" in context
        has_gds = "gds_path" in context

        if not has_paper and not has_gds:
            return self._make_error(
                "No input provided. Need paper_text/pdf_path for analysis or gds_path for conversion.",
                suggestions=["Provide paper_text, pdf_path, or gds_path"]
            )

        return self._make_success(
            message="PDK Agent ready to process",
            result={
                "has_paper": has_paper,
                "has_gds": has_gds,
                "target_pdk": context.get("target_pdk"),
                "status": "ready",
                "next_action": "analyze_paper_process" if has_paper else "match_pdk"
            },
            metrics={},
            next_steps=[
                "Analyze paper for process info" if has_paper else "Skip",
                "Match to compatible PDKs",
                "Get layer mapping",
                "Convert GDS" if has_gds else "Skip",
                "Run DRC" if has_gds else "Skip"
            ]
        )


# Factory function
def create_pdk_agent() -> PDKAgent:
    """Create a PDK agent instance."""
    return PDKAgent()
