"""
Raphael MCP Server - Orchestrator-Driven GDS Generation

Provides primitive tools for the orchestrator (Claude Code) to build GDS files:
- execute_gds_script: Run GDSFactory Python scripts
- rasterize_and_compare: Compute IoU/Dice metrics against target
- get_gds_catalog: Access GDSFactory function reference
- get_target_image: Get target image and footprint info

The orchestrator writes scripts, executes them, sees results, and iterates.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp.types import TextContent, Tool

import michaelangelo

from .base import BaseMCPServer, serialize_result, tool_handler

logger = logging.getLogger(__name__)

# Thread pool for blocking operations
_executor = ThreadPoolExecutor(max_workers=4)

# Path to michaelangelo core scripts (resolved from the installed package)
MICHAELANGELO_DIR = Path(michaelangelo.__file__).parent
COMPARE_SCRIPT = MICHAELANGELO_DIR / "core" / "compare_absolute.py"
CATALOG_EXTENDED_PATH = MICHAELANGELO_DIR / "reference" / "gds_factory_function_catalogue_extended.md"
# Only the extended catalog exists in-repo; use it as the default as well.
CATALOG_PATH = CATALOG_EXTENDED_PATH


class RaphaelServer(BaseMCPServer):
    """
    MCP Server for Orchestrator-Driven GDS Generation.

    Provides primitive tools for the orchestrator to:
    1. Set up component directories
    2. Run calibration
    3. Execute GDSFactory scripts
    4. Rasterize and compare against targets
    5. Access the GDSFactory function catalog

    The orchestrator (Claude Code) is responsible for:
    - Writing the GDSFactory Python scripts
    - Iterating based on IoU metrics
    - Making intelligent decisions about improvements
    """

    server_name = "homi-raphael"
    server_version = "0.1.0"

    def get_tools(self) -> List[Tool]:
        return [
            # Setup tools (kept from v0.1.0)
            Tool(
                name="setup_component_directory",
                description=(
                    "Initialize a component directory with the required structure for GDS generation. "
                    "Copies the device image and creates footprint.json."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "image_path": {
                            "type": "string",
                            "description": "Path to the B&W device image"
                        },
                        "output_dir": {
                            "type": "string",
                            "description": "Directory to set up as component directory"
                        },
                        "footprint": {
                            "type": "object",
                            "description": "Device footprint in micrometers",
                            "properties": {
                                "length_um": {"type": "number"},
                                "width_um": {"type": "number"}
                            },
                            "required": ["length_um", "width_um"]
                        }
                    },
                    "required": ["image_path", "output_dir", "footprint"]
                }
            ),
            Tool(
                name="run_calibration",
                description=(
                    "Generate calibration.json for image-to-physical space mapping. "
                    "Required before running rasterize_and_compare."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "component_dir": {
                            "type": "string",
                            "description": "Path to component directory (must contain component.png and footprint.json)"
                        }
                    },
                    "required": ["component_dir"]
                }
            ),
            # NEW: Orchestrator-driven tools
            Tool(
                name="execute_gds_script",
                description=(
                    "Execute a GDSFactory Python script and return the GDS file path. "
                    "The script should create a component and call write_gds() to save it."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "script_path": {
                            "type": "string",
                            "description": "Path to Python script containing GDSFactory code"
                        },
                        "output_dir": {
                            "type": "string",
                            "description": "Directory for GDS output (defaults to script directory)"
                        },
                        "timeout_seconds": {
                            "type": "integer",
                            "description": "Execution timeout in seconds (default: 120)",
                            "default": 120
                        }
                    },
                    "required": ["script_path"]
                }
            ),
            Tool(
                name="rasterize_and_compare",
                description=(
                    "Rasterize a GDS file and compute comparison metrics against target image. "
                    "Returns IoU (the cost function), Dice, SSE, and paths to visualization images. "
                    "IoU ranges from 0 to 1 (higher is better)."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "gds_path": {
                            "type": "string",
                            "description": "Path to GDS file to rasterize"
                        },
                        "target_image": {
                            "type": "string",
                            "description": "Path to target B&W device image"
                        },
                        "calibration_path": {
                            "type": "string",
                            "description": "Path to calibration.json"
                        },
                        "output_dir": {
                            "type": "string",
                            "description": "Directory to save output images (raster, diff, overlay)"
                        },
                        "layer": {
                            "type": "integer",
                            "description": "GDS layer to extract (default: 1)",
                            "default": 1
                        },
                        "datatype": {
                            "type": "integer",
                            "description": "GDS datatype to extract (default: 0)",
                            "default": 0
                        }
                    },
                    "required": ["gds_path", "target_image", "calibration_path", "output_dir"]
                }
            ),
            Tool(
                name="get_gds_catalog",
                description=(
                    "Get the GDSFactory function catalog for reference. "
                    "Returns available functions for creating photonic components. "
                    "Use 'extended' mode for the full detailed catalog."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "extended": {
                            "type": "boolean",
                            "description": "Return extended catalog with more detail (default: false)",
                            "default": False
                        }
                    }
                }
            ),
            Tool(
                name="get_target_image",
                description=(
                    "Get information about the target image for a component directory. "
                    "Returns the image path, footprint, and calibration data."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "component_dir": {
                            "type": "string",
                            "description": "Path to component directory"
                        }
                    },
                    "required": ["component_dir"]
                }
            ),
        ]

    async def handle_tool(self, name: str, arguments: Dict[str, Any]) -> List[TextContent]:
        """Dispatch tool calls to handlers."""
        handlers = {
            "setup_component_directory": self._setup_component_directory,
            "run_calibration": self._run_calibration,
            "execute_gds_script": self._execute_gds_script,
            "rasterize_and_compare": self._rasterize_and_compare,
            "get_gds_catalog": self._get_gds_catalog,
            "get_target_image": self._get_target_image,
        }

        handler = handlers.get(name)
        if not handler:
            return [TextContent(
                type="text",
                text=serialize_result({"status": "error", "error": f"Unknown tool: {name}"})
            )]

        return await handler(arguments)

    @tool_handler
    async def _setup_component_directory(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Set up component directory with required structure."""
        image_path = Path(args["image_path"])
        output_dir = Path(args["output_dir"])
        footprint = args["footprint"]

        if not image_path.exists():
            return {"status": "error", "error": f"Image not found: {image_path}"}

        # Create directory structure
        output_dir.mkdir(parents=True, exist_ok=True)

        # Copy image as component.png
        component_image = output_dir / "component.png"
        shutil.copy2(image_path, component_image)

        # Create footprint.json
        footprint_data = {
            "footprint_um": [footprint["length_um"], footprint["width_um"]]
        }
        footprint_path = output_dir / "footprint.json"
        with open(footprint_path, "w") as f:
            json.dump(footprint_data, f, indent=2)

        return {
            "status": "success",
            "component_dir": str(output_dir),
            "files_created": [
                str(component_image),
                str(footprint_path)
            ],
            "footprint_um": footprint_data["footprint_um"],
            "next_step": "Run run_calibration to generate calibration.json"
        }

    @tool_handler
    async def _run_calibration(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Generate calibration file using homi.jee_integration."""
        component_dir = Path(args["component_dir"])

        # Check required files
        component_image = component_dir / "component.png"
        footprint_path = component_dir / "footprint.json"

        if not component_image.exists():
            return {"status": "error", "error": f"component.png not found in {component_dir}"}
        if not footprint_path.exists():
            return {"status": "error", "error": f"footprint.json not found in {component_dir}"}

        calibration_path = component_dir / "calibration.json"

        try:
            from homi.jee_integration import prepare_calibration

            loop = asyncio.get_event_loop()
            result_path = await loop.run_in_executor(
                _executor,
                lambda: prepare_calibration(
                    target_image_path=component_image,
                    footprint_json_path=footprint_path,
                    output_path=calibration_path
                )
            )

            # Read the generated calibration
            with open(result_path) as f:
                calibration = json.load(f)

            return {
                "status": "success",
                "calibration_path": str(result_path),
                "calibration": calibration,
                "next_step": "View target image with get_target_image, then write a GDSFactory script"
            }

        except Exception as e:
            return {"status": "error", "error": f"Calibration failed: {e}"}

    @tool_handler
    async def _execute_gds_script(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a GDSFactory Python script and return the GDS file path."""
        script_path = Path(args["script_path"])
        output_dir = Path(args.get("output_dir") or script_path.parent)
        timeout = args.get("timeout_seconds", 120)

        if not script_path.exists():
            return {"status": "error", "error": f"Script not found: {script_path}"}

        output_dir.mkdir(parents=True, exist_ok=True)

        # Track existing GDS files to find new ones
        existing_gds = set(output_dir.glob("*.gds"))

        loop = asyncio.get_event_loop()

        def run_script():
            start_time = time.time()
            try:
                result = subprocess.run(
                    [sys.executable, str(script_path)],
                    cwd=str(output_dir),
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )
                execution_time = time.time() - start_time

                # Find newly created GDS files
                current_gds = set(output_dir.glob("*.gds"))
                new_gds = current_gds - existing_gds

                # If no new files, look for most recent GDS
                if not new_gds and current_gds:
                    new_gds = {max(current_gds, key=lambda p: p.stat().st_mtime)}

                gds_path = None
                if new_gds:
                    # Get the most recently modified GDS
                    gds_path = str(max(new_gds, key=lambda p: p.stat().st_mtime))

                return {
                    "success": result.returncode == 0,
                    "gds_path": gds_path,
                    "stdout": result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout,
                    "stderr": result.stderr[-2000:] if len(result.stderr) > 2000 else result.stderr,
                    "return_code": result.returncode,
                    "execution_time_seconds": round(execution_time, 2)
                }

            except subprocess.TimeoutExpired:
                return {
                    "success": False,
                    "error": f"Script execution timed out after {timeout} seconds",
                    "gds_path": None
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "gds_path": None
                }

        result = await loop.run_in_executor(_executor, run_script)

        if result["success"] and result["gds_path"]:
            result["status"] = "success"
            result["next_step"] = "Use rasterize_and_compare to compute IoU metrics"
        else:
            result["status"] = "error"
            if not result.get("error"):
                result["error"] = result.get("stderr", "Unknown error during execution")

        return result

    @tool_handler
    async def _rasterize_and_compare(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Rasterize a GDS file and compute comparison metrics."""
        gds_path = Path(args["gds_path"])
        target_image = Path(args["target_image"])
        calibration_path = Path(args["calibration_path"])
        output_dir = Path(args["output_dir"])
        layer = args.get("layer", 1)
        datatype = args.get("datatype", 0)

        # Validate inputs
        if not gds_path.exists():
            return {"status": "error", "error": f"GDS file not found: {gds_path}"}
        if not target_image.exists():
            return {"status": "error", "error": f"Target image not found: {target_image}"}
        if not calibration_path.exists():
            return {"status": "error", "error": f"Calibration file not found: {calibration_path}"}
        if not COMPARE_SCRIPT.exists():
            return {"status": "error", "error": f"Compare script not found: {COMPARE_SCRIPT}"}

        output_dir.mkdir(parents=True, exist_ok=True)

        # Output file paths
        raster_path = output_dir / "raster.png"
        diff_path = output_dir / "diff.png"
        overlay_path = output_dir / "overlay.png"
        metrics_path = output_dir / "metrics.json"

        loop = asyncio.get_event_loop()

        def run_compare():
            try:
                cmd = [
                    sys.executable, str(COMPARE_SCRIPT),
                    "--gds", str(gds_path),
                    "--target", str(target_image),
                    "--calibration", str(calibration_path),
                    "--out-raster", str(raster_path),
                    "--out-diff", str(diff_path),
                    "--out-overlay", str(overlay_path),
                    "--out-metrics", str(metrics_path),
                    "--layer", str(layer),
                    "--datatype", str(datatype)
                ]

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=60
                )

                if result.returncode != 0:
                    return {
                        "success": False,
                        "error": result.stderr or "Comparison failed"
                    }

                # Read metrics
                with open(metrics_path) as f:
                    metrics = json.load(f)

                return {
                    "success": True,
                    "metrics": metrics
                }

            except subprocess.TimeoutExpired:
                return {"success": False, "error": "Comparison timed out"}
            except Exception as e:
                return {"success": False, "error": str(e)}

        result = await loop.run_in_executor(_executor, run_compare)

        if not result["success"]:
            return {"status": "error", "error": result["error"]}

        metrics = result["metrics"]

        return {
            "status": "success",
            "metrics": {
                "IoU": metrics.get("IoU", 0),  # PRIMARY COST FUNCTION - higher is better
                "Dice": metrics.get("Dice", 0),
                "SSE": metrics.get("SSE", 0),  # Lower is better
                "MSE": metrics.get("MSE", 0),
                "Accuracy": metrics.get("Accuracy", 0),
                "Precision": metrics.get("Precision", 0),
                "Recall": metrics.get("Recall", 0),
            },
            "images": {
                "raster": str(raster_path),      # What the GDS looks like
                "diff": str(diff_path),          # Red=FP, Blue=FN - shows where to improve
                "overlay": str(overlay_path)     # GDS overlaid on target
            },
            "size_info": {
                "gds_size_um": metrics.get("gds_size_um", [0, 0]),
                "footprint_um": metrics.get("footprint_um", [0, 0]),
                "size_match": metrics.get("size_match", [False, False])
            },
            "interpretation": {
                "iou_quality": (
                    "excellent" if metrics.get("IoU", 0) >= 0.7 else
                    "good" if metrics.get("IoU", 0) >= 0.5 else
                    "fair" if metrics.get("IoU", 0) >= 0.3 else
                    "poor"
                ),
                "suggestion": (
                    "View diff.png to see red (extra material) and blue (missing material) regions. "
                    "Adjust your script to reduce these differences."
                )
            }
        }

    @tool_handler
    async def _get_gds_catalog(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get the GDSFactory function catalog."""
        extended = args.get("extended", False)

        catalog_path = CATALOG_EXTENDED_PATH if extended else CATALOG_PATH

        if not catalog_path.exists():
            return {"status": "error", "error": f"Catalog not found: {catalog_path}"}

        try:
            content = catalog_path.read_text()

            return {
                "status": "success",
                "catalog_type": "extended" if extended else "standard",
                "catalog": content,
                "usage_hint": (
                    "Use these GDSFactory functions to create your component. "
                    "Import gdsfactory as gf, create a function that returns gf.Component, "
                    "and call component.write_gds('output.gds') at the end."
                )
            }

        except Exception as e:
            return {"status": "error", "error": f"Failed to read catalog: {e}"}

    @tool_handler
    async def _get_target_image(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get information about the target image for a component directory."""
        component_dir = Path(args["component_dir"])

        # Check for component image
        component_image = component_dir / "component.png"
        if not component_image.exists():
            return {"status": "error", "error": f"component.png not found in {component_dir}"}

        # Load footprint
        footprint_path = component_dir / "footprint.json"
        footprint = None
        if footprint_path.exists():
            with open(footprint_path) as f:
                footprint_data = json.load(f)
                footprint = footprint_data.get("footprint_um")

        # Load calibration if available
        calibration_path = component_dir / "calibration.json"
        calibration = None
        if calibration_path.exists():
            with open(calibration_path) as f:
                calibration = json.load(f)

        # Get image dimensions
        from PIL import Image
        with Image.open(component_image) as img:
            image_size = img.size

        return {
            "status": "success",
            "image_path": str(component_image),
            "image_size_px": list(image_size),
            "footprint_um": footprint,
            "calibration_path": str(calibration_path) if calibration else None,
            "calibration": calibration,
            "ready_for_generation": calibration is not None,
            "workflow_hint": (
                "1. View the image at image_path to understand the device structure\n"
                "2. Use get_gds_catalog to see available GDSFactory functions\n"
                "3. Write a Python script using GDSFactory to recreate the device\n"
                "4. Execute with execute_gds_script\n"
                "5. Compare with rasterize_and_compare (target IoU > 0.5)\n"
                "6. View diff.png, adjust script, and iterate"
            )
        }


# Entry point
async def main():
    logging.basicConfig(level=logging.INFO)
    server = RaphaelServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
