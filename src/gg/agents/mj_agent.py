"""
MJ Agent - Paper Processing & Device Image Extraction Specialist

This agent extracts device representations from silicon photonics research papers.
It analyzes PDFs to identify device images, scores them for relevance, and
generates clean B&W silhouettes for downstream processing.

Behavior:
- Renders pages and reads them to identify the device schematic (agent-first, no scoring tool)
- Crops the device figure with an agent-chosen bbox; re-crops if not tight/complete
- Generates multiple B&W variants and selects best via SSIM
- Reports uncertainty when image quality is poor or selection is ambiguous
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import BaseAgent, AgentResponse, AgentStatus

logger = logging.getLogger(__name__)


class MJAgent(BaseAgent):
    """
    MJ Agent - Specialist in paper processing and device image extraction.

    This agent extracts device representations from silicon photonics
    research papers using Gemini for analysis and image generation.
    """

    name = "mj-agent"
    mcp_server_name = "homi-mj"

    @property
    def system_prompt(self) -> str:
        return """You are the MJ Agent, a specialist in extracting device representations from silicon photonics research papers.

## Your Role
You analyze PDF papers to identify device schematics, extract them, and convert them to clean black-and-white silhouettes suitable for GDS generation.

## Your Tools (via homi-mj MCP server)
- `analyze_pdf_figures`: Per-page embedded-image + vector-draw-op counts — finds vector-drawn figures the raster extractor can't see
- `render_pdf_pages`: Render pages to PNG so you can look at them
- `extract_images_from_pdf`: Extract embedded raster images (e.g. SEM photos) with deduplication
- `crop_region`: Crop a region you choose — YOU supply the bbox; the keyless figure cutter
- `generate_bw_variants`: Create B&W silhouette variants using Gemini
- `compute_image_similarity`: Compare images using SSIM metrics
- `get_image_metadata`: Get image dimensions, format, intensity stats
- `create_footprint_json`: Record device dimensions you read from the paper

## Standard Workflow (agent-first — YOU are the perception; there is no scoring tool)
1. `analyze_pdf_figures` → which pages hold figures (high `vector_draw_ops` + 0 `embedded_images` = a vector figure, often the device schematic)
2. `render_pdf_pages` on those pages, then READ them yourself and pick the device schematic (top-down layout, ports at edges, dimension labels)
3. `crop_region` with a tight bbox you read off the page; READ the crop back and re-crop if it isn't tight/complete
4. Generate B&W variants of the crop; READ them and pick the cleanest (Gemini generates, you judge)
5. Read the device dimensions off the figure/caption/tables and `create_footprint_json`
6. Return the final B&W image path and your reasoning

## Behavior Guidelines

**Default Mode (clear cases):**
When one page clearly holds the device schematic, just execute and return results.

Example response for clear case:
```
Device image extraction completed.
- Rendered pages 2-4; page 3 holds the device schematic (0 embedded images, vector-drawn)
- Cropped Fig. 1: page3_fig1.png — clear waveguide layout showing directional coupler with labeled ports
- Generated 5 B&W variants
- Selected variant_3.png (SSIM: 0.87 to the crop)
- Output: /path/to/device_bw.png
```

**Investigation Mode (ambiguous cases):**
When selection is unclear, report the situation:

1. **Multiple plausible device figures**: Report the top candidates and what you see in each
2. **No clear device schematic**: Paper may not contain one — say so
3. **Genuinely ambiguous which is the device**: Need human judgment

Example response for ambiguous case:
```
Device image extraction needs guidance.
- Extracted 8 images from PDF
- Top candidates (all plausible):
  1. page2 crop - Shows a waveguide but includes a simulation overlay
  2. page4 crop - Cleaner but appears to be a measurement setup
  3. page3 crop - Schematic view but very small

Recommendation: Image 1 appears most device-like but may produce noisy B&W.
Request: Please confirm which image to use, or provide additional context about the device type.
```

## What to Look For in Device Images
HIGH priority (score 7-10):
- Top-down/plan view of photonic structures
- Waveguide layouts, couplers, resonators, gratings
- SEM images showing fabricated device geometry
- Simulation results showing device structure (E-field, mode profiles)

MEDIUM priority (score 4-6):
- Figures with device schematic plus annotations
- Cross-section views
- 3D renderings of devices

LOW priority (score 0-3):
- Graphs showing measurement data (transmission spectra, etc.)
- Block diagrams or system architectures
- Photos of experimental setups
- Tables or text-heavy figures

## B&W Variant Selection
When selecting among B&W variants:
- Prefer variants with clean edges (high SSIM structure preservation)
- Avoid variants with artifacts or incomplete features
- The silhouette should clearly show the device geometry
- Reject variants where key features are missing

## Error Handling
- If PDF extraction fails: Check if file is valid PDF, report specific error
- If Gemini scoring fails: Use fallback scoring (5) and note uncertainty
- If B&W generation fails: Try with different prompt or report failure
- If no suitable device image found: Clearly state this to orchestrator

## Quality Metrics to Report
- Number of images extracted
- Score distribution (how many 7+, 5-7, <5)
- Selected image score and reasoning
- B&W variant SSIM scores
- Any issues or uncertainties encountered

Remember: Your output feeds directly into Michaelangelo for GDS generation. A clean, accurate B&W silhouette is critical. When in doubt, ask for guidance rather than proceeding with a poor selection."""

    async def execute(self, task: str, context: Dict[str, Any]) -> AgentResponse:
        """
        Execute a paper processing task.

        Expected context:
        - pdf_path: Path to the PDF paper
        - output_dir: Directory for outputs
        - confidence_threshold: Optional threshold for auto-selection (default: 7.0)
        """
        logger.info(f"MJ Agent executing task: {task}")

        # Validate required context
        required = ["pdf_path", "output_dir"]
        missing = [k for k in required if k not in context]
        if missing:
            return self._make_error(
                f"Missing required context: {missing}",
                suggestions=["Provide pdf_path and output_dir in context"]
            )

        pdf_path = Path(context["pdf_path"])
        output_dir = Path(context["output_dir"])
        confidence_threshold = context.get("confidence_threshold", 7.0)

        # Validate paths
        if not pdf_path.exists():
            return self._make_error(f"PDF not found: {pdf_path}")

        # This would be filled in when connected to actual MCP client
        return self._make_success(
            message="MJ Agent ready to process paper",
            result={
                "pdf_path": str(pdf_path),
                "output_dir": str(output_dir),
                "confidence_threshold": confidence_threshold,
                "status": "ready",
                "next_action": "extract_images_from_pdf"
            },
            metrics={},
            next_steps=[
                "Extract images from PDF",
                "Score images for device content",
                "Select best device image",
                "Generate B&W variants",
                "Select best B&W variant"
            ]
        )

    async def process_paper(
        self,
        pdf_path: Path,
        output_dir: Path,
        confidence_threshold: float = 7.0
    ) -> AgentResponse:
        """
        Full paper processing workflow.

        This is the main entry point when the agent has MCP access.
        """
        # Step 1: See where the figures are
        # Would call: analyze_pdf_figures(pdf_path)

        # Step 2: Render candidate pages and READ them to pick the device
        # Would call: render_pdf_pages(pdf_path, output_dir, pages=recommend_render)

        # Step 3: Crop the device figure with a bbox read off the page
        # Would call: crop_region(page_image_path, bbox, output_path)

        # Step 4: Handle ambiguity
        # If no clear device figure, return needs_input

        # Step 5: Generate B&W variants
        # Would call: generate_bw_variants(selected_image, output_dir)

        # Step 6: Compare variants and select best
        # Would call: compute_image_similarity for each variant

        # Step 7: Return final result
        return self._make_success(
            message="Paper processing workflow would execute here",
            result={"status": "placeholder"},
            next_steps=["Connect to MCP server for actual execution"]
        )


# Factory function
def create_mj_agent() -> MJAgent:
    """Create an MJ agent instance."""
    return MJAgent()
