"""
Flex MCP Server - Tidy3D FDTD Simulation

Tools for creating and uploading FDTD simulations to Tidy3D cloud.
Provides simulation workflow for Step 8 of the HOMI pipeline.
"""

from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp.types import TextContent, Tool

from .base import BaseMCPServer, serialize_result, tool_handler

logger = logging.getLogger(__name__)

# Thread pool for blocking operations
_executor = ThreadPoolExecutor(max_workers=4)


class FlexServer(BaseMCPServer):
    """
    MCP Server for Tidy3D FDTD simulation.

    Provides tools for:
    - Checking Tidy3D availability
    - Listing material presets
    - Validating API keys
    - Creating simulations from GDS files
    - Uploading simulations to Tidy3D cloud
    - Checking simulation task status
    """

    server_name = "homi-flex"
    server_version = "0.1.0"

    def get_tools(self) -> List[Tool]:
        return [
            Tool(
                name="is_tidy3d_available",
                description=(
                    "Check if Tidy3D and required dependencies are available. "
                    "Returns availability status and version info."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            Tool(
                name="get_material_presets",
                description=(
                    "Get available material presets for simulation. "
                    "Each preset includes core and cladding refractive indices."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            Tool(
                name="validate_api_key",
                description=(
                    "Validate a Tidy3D API key by attempting to authenticate. "
                    "Returns whether the key is valid."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "api_key": {
                            "type": "string",
                            "description": "Tidy3D API key to validate"
                        }
                    },
                    "required": ["api_key"]
                }
            ),
            Tool(
                name="get_simulation_info",
                description=(
                    "Get information about simulation that would be created from a GDS file. "
                    "Returns simulation parameters without creating or uploading."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "gds_path": {
                            "type": "string",
                            "description": "Path to GDS file"
                        },
                        "layers": {
                            "type": "array",
                            "items": {
                                "type": "array",
                                "items": {"type": "integer"},
                                "minItems": 2,
                                "maxItems": 2
                            },
                            "description": "Layers to include as (layer, datatype) pairs",
                            "default": [[1, 0]]
                        },
                        "thickness_nm": {
                            "type": "integer",
                            "description": "Device thickness in nm (default: 220)",
                            "default": 220
                        },
                        "wavelength_um": {
                            "type": "number",
                            "description": "Simulation wavelength in um (default: 1.55)",
                            "default": 1.55
                        }
                    },
                    "required": ["gds_path"]
                }
            ),
            Tool(
                name="create_and_upload_simulation",
                description=(
                    "Create a Tidy3D simulation from a GDS file and upload to cloud. "
                    "Returns task ID and Workbench URL for monitoring."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "gds_path": {
                            "type": "string",
                            "description": "Path to GDS file"
                        },
                        "api_key": {
                            "type": "string",
                            "description": "Tidy3D API key"
                        },
                        "material": {
                            "type": "string",
                            "description": "Material preset name (default: 'Silicon (SOI)')",
                            "default": "Silicon (SOI)"
                        },
                        "thickness_nm": {
                            "type": "integer",
                            "description": "Device thickness in nm (default: 220)",
                            "default": 220
                        },
                        "wavelength_um": {
                            "type": "number",
                            "description": "Simulation wavelength in um (default: 1.55)",
                            "default": 1.55
                        },
                        "layers": {
                            "type": "array",
                            "items": {
                                "type": "array",
                                "items": {"type": "integer"},
                                "minItems": 2,
                                "maxItems": 2
                            },
                            "description": "Layers to include as (layer, datatype) pairs",
                            "default": [[1, 0]]
                        },
                        "custom_core_n": {
                            "type": "number",
                            "description": "Custom core refractive index (for Custom preset)"
                        },
                        "custom_clad_n": {
                            "type": "number",
                            "description": "Custom cladding refractive index (for Custom preset)"
                        },
                        "task_name": {
                            "type": "string",
                            "description": "Name for the task (default: 'HOMI_Device')",
                            "default": "HOMI_Device"
                        }
                    },
                    "required": ["gds_path", "api_key"]
                }
            ),
            Tool(
                name="run_parameter_sweep",
                description=(
                    "Budgeted batch parameter sweep: grid over a device script's declared "
                    "top-level tunables, one small FDTD task per grid point, all uploaded "
                    "first and started only if the summed cost estimate fits the budget. "
                    "Measure-only (no search). fom currently: coupling_ratio. "
                    "Use dry_run=true to preview the grid without any cloud calls."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "script_path": {"type": "string", "description": "Parametric device script (top-level name = value tunables)"},
                        "stack_json_path": {"type": "string", "description": "Layer stack JSON (core_n, clad_n, thickness_um)"},
                        "sweep": {"type": "object", "description": "{tunable_name: [values,...]} full cartesian grid"},
                        "fom": {"type": "string", "enum": ["coupling_ratio"]},
                        "budget_fc": {"type": "number", "description": "Hard total FlexCredit ceiling; abort if estimates exceed"},
                        "out_path": {"type": "string"},
                        "dry_run": {"type": "boolean"}
                    },
                    "required": ["script_path", "stack_json_path", "sweep", "fom", "budget_fc"]
                }
            ),
            Tool(
                name="get_task_status",
                description=(
                    "Get the current status of a Tidy3D simulation task. "
                    "Returns status string (e.g., 'queued', 'running', 'success', 'error')."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "string",
                            "description": "Task ID from create_and_upload_simulation"
                        }
                    },
                    "required": ["task_id"]
                }
            ),
            Tool(
                name="get_workbench_url",
                description=(
                    "Get the Tidy3D Workbench URL for a task. "
                    "Opens the simulation in Tidy3D's web interface."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "string",
                            "description": "Task ID"
                        }
                    },
                    "required": ["task_id"]
                }
            )
        ]

    async def handle_tool(self, name: str, arguments: Dict[str, Any]) -> List[TextContent]:
        """Dispatch tool calls to handlers."""
        handlers = {
            "is_tidy3d_available": self._is_tidy3d_available,
            "get_material_presets": self._get_material_presets,
            "validate_api_key": self._validate_api_key,
            "get_simulation_info": self._get_simulation_info,
            "create_and_upload_simulation": self._create_and_upload_simulation,
            "run_parameter_sweep": self._run_parameter_sweep,
            "get_task_status": self._get_task_status,
            "get_workbench_url": self._get_workbench_url,
        }

        handler = handlers.get(name)
        if not handler:
            return [TextContent(
                type="text",
                text=serialize_result({"status": "error", "error": f"Unknown tool: {name}"})
            )]

        return await handler(arguments)

    @tool_handler
    async def _is_tidy3d_available(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Check if Tidy3D is available."""
        loop = asyncio.get_event_loop()

        def check():
            try:
                from homi.flex_integration import is_tidy3d_available
                available = is_tidy3d_available()

                result = {"available": available}

                if available:
                    try:
                        import tidy3d
                        result["tidy3d_version"] = tidy3d.__version__
                    except Exception:
                        pass

                    try:
                        import gdstk
                        result["gdstk_available"] = True
                    except ImportError:
                        result["gdstk_available"] = False

                return result

            except ImportError as e:
                return {
                    "available": False,
                    "error": f"Flex module not available: {e}"
                }

        result = await loop.run_in_executor(_executor, check)
        return {"status": "success", **result}

    @tool_handler
    async def _get_material_presets(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get available material presets."""
        loop = asyncio.get_event_loop()

        def get_presets():
            try:
                from homi.flex_integration import get_material_presets
                presets = get_material_presets()
                return {"presets": presets}
            except ImportError as e:
                return {"presets": {}, "error": str(e)}

        result = await loop.run_in_executor(_executor, get_presets)
        return {"status": "success", **result}

    @tool_handler
    async def _validate_api_key(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a Tidy3D API key."""
        api_key = args["api_key"]

        loop = asyncio.get_event_loop()

        def validate():
            try:
                from homi.flex_integration import validate_api_key
                valid = validate_api_key(api_key)
                return {"valid": valid}
            except ImportError as e:
                return {"valid": False, "error": str(e)}

        result = await loop.run_in_executor(_executor, validate)
        return {"status": "success", **result}

    @tool_handler
    async def _get_simulation_info(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get simulation info without creating."""
        gds_path = Path(args["gds_path"])
        layers = [tuple(l) for l in args.get("layers", [[1, 0]])]
        thickness_nm = args.get("thickness_nm", 220)
        wavelength_um = args.get("wavelength_um", 1.55)

        if not gds_path.exists():
            return {"status": "error", "error": f"GDS not found: {gds_path}"}

        loop = asyncio.get_event_loop()

        def get_info():
            try:
                import gdsfactory as gf
                from homi.flex_integration import get_simulation_info

                component = gf.import_gds(str(gds_path))
                info = get_simulation_info(component, layers, thickness_nm, wavelength_um)
                return info
            except ImportError as e:
                return {"error": f"Import failed: {e}"}
            except Exception as e:
                return {"error": str(e)}

        result = await loop.run_in_executor(_executor, get_info)

        if "error" in result:
            return {"status": "error", **result}

        return {"status": "success", "simulation_info": result}

    @tool_handler
    async def _create_and_upload_simulation(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Create and upload simulation to Tidy3D cloud."""
        gds_path = Path(args["gds_path"])
        api_key = args["api_key"]

        if not gds_path.exists():
            return {"status": "error", "error": f"GDS not found: {gds_path}"}

        # Build config
        config = {
            "material": args.get("material", "Silicon (SOI)"),
            "thickness_nm": args.get("thickness_nm", 220),
            "wavelength_um": args.get("wavelength_um", 1.55),
            "layers": [tuple(l) for l in args.get("layers", [[1, 0]])],
            "task_name": args.get("task_name", "HOMI_Device"),
        }

        if "custom_core_n" in args:
            config["custom_core_n"] = args["custom_core_n"]
        if "custom_clad_n" in args:
            config["custom_clad_n"] = args["custom_clad_n"]

        loop = asyncio.get_event_loop()

        def create_upload():
            try:
                import gdsfactory as gf
                from homi.flex_integration import create_and_upload_simulation

                component = gf.import_gds(str(gds_path))
                result = create_and_upload_simulation(
                    component=component,
                    config=config,
                    api_key=api_key
                )
                return result
            except ImportError as e:
                return {"error": f"Import failed: {e}"}
            except RuntimeError as e:
                return {"error": str(e)}
            except Exception as e:
                return {"error": str(e)}

        result = await loop.run_in_executor(_executor, create_upload)

        if "error" in result:
            return {"status": "error", **result}

        return {
            "status": "success",
            "task_id": result.get("task_id"),
            "web_url": result.get("web_url"),
            "estimated_cost": result.get("estimated_cost"),
            "simulation_info": result.get("simulation_info", {})
        }

    @tool_handler
    async def _run_parameter_sweep(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Budgeted batch sweep over a script's declared tunables (measure-only)."""
        loop = asyncio.get_event_loop()

        def sweep():
            try:
                from homi.sweep_evaluation import run_sweep
                return run_sweep(
                    script_path=args["script_path"],
                    stack_json_path=args["stack_json_path"],
                    sweep=args["sweep"],
                    fom=args["fom"],
                    budget_fc=float(args["budget_fc"]),
                    out_path=args.get("out_path"),
                    dry_run=bool(args.get("dry_run", False)),
                )
            except Exception as e:  # surfaced to the caller verbatim
                return {"error": str(e)}

        result = await loop.run_in_executor(_executor, sweep)
        if "error" in result:
            return {"status": "error", **result}
        return {"status": "success", "sweep": result}

    @tool_handler
    async def _get_task_status(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get task status from Tidy3D cloud."""
        task_id = args["task_id"]

        loop = asyncio.get_event_loop()

        def get_status():
            try:
                from homi.flex_integration import get_task_status
                status = get_task_status(task_id)
                return {"task_status": status}
            except ImportError as e:
                return {"error": str(e)}

        result = await loop.run_in_executor(_executor, get_status)

        if "error" in result:
            return {"status": "error", **result}

        return {"status": "success", **result}

    @tool_handler
    async def _get_workbench_url(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get Tidy3D Workbench URL for a task."""
        task_id = args["task_id"]

        loop = asyncio.get_event_loop()

        def get_url():
            try:
                from homi.flex_integration import get_workbench_url
                url = get_workbench_url(task_id)
                return {"url": url}
            except ImportError as e:
                # Fallback URL construction
                return {"url": f"https://tidy3d.simulation.cloud/workbench?taskId={task_id}"}

        result = await loop.run_in_executor(_executor, get_url)

        return {"status": "success", **result}


# Entry point
async def main():
    logging.basicConfig(level=logging.INFO)
    server = FlexServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
