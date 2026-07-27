"""
JEE MCP Server - GDS Parameter Optimization

Tools for fine-tuning parametric GDS scripts to match target images
using numerical optimization (Powell/Nelder-Mead).
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from mcp.types import TextContent, Tool

from .base import BaseMCPServer, TaskStatus, serialize_result, tool_handler

# Import JEE core modules (for compute_sse only - optimization uses homi.jee_integration)
from jee.core import compute_sse as sse_mod

logger = logging.getLogger(__name__)

# Thread pool for blocking operations
_executor = ThreadPoolExecutor(max_workers=2)


class JEEServer(BaseMCPServer):
    """
    MCP Server for JEE (GDS Optimization).

    Provides tools for:
    - Extracting parameters from GDSFactory scripts
    - Computing SSE metrics between target and generated images
    - Running optimization to minimize SSE
    - Applying optimized parameters to scripts
    """

    server_name = "homi-jee"
    server_version = "0.1.0"

    def get_tools(self) -> List[Tool]:
        return [
            Tool(
                name="extract_parameters",
                description=(
                    "Extract tunable parameters from a GDSFactory Python script. "
                    "Analyzes the script to find numeric parameters with their current "
                    "values and suggests reasonable bounds for optimization."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "script_path": {
                            "type": "string",
                            "description": "Path to the GDSFactory Python script"
                        }
                    },
                    "required": ["script_path"]
                }
            ),
            Tool(
                name="compute_sse",
                description=(
                    "Compute Sum of Squared Errors (SSE) and related metrics between "
                    "a target image and a rasterized GDS image. Returns SSE, MSE, RMSE, "
                    "and pixel-level breakdown."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "target_image": {
                            "type": "string",
                            "description": "Path to target image (PNG)"
                        },
                        "raster_image": {
                            "type": "string",
                            "description": "Path to rasterized GDS image (PNG)"
                        },
                        "white_threshold": {
                            "type": "integer",
                            "description": "Threshold for white pixels (default: 245)",
                            "default": 245
                        }
                    },
                    "required": ["target_image", "raster_image"]
                }
            ),
            Tool(
                name="run_optimization",
                description=(
                    "Start an optimization run to minimize SSE between generated GDS "
                    "and target image. Returns a task_id for polling progress. "
                    "This is a long-running operation."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "script_path": {
                            "type": "string",
                            "description": "Path to the GDSFactory Python script"
                        },
                        "target_image": {
                            "type": "string",
                            "description": "Path to target image (PNG)"
                        },
                        "calibration_file": {
                            "type": "string",
                            "description": "Path to calibration.json"
                        },
                        "output_dir": {
                            "type": "string",
                            "description": "Directory for optimization outputs"
                        },
                        "param_bounds": {
                            "type": "object",
                            "description": "Dict mapping param name to [min, max] bounds",
                            "additionalProperties": {
                                "type": "array",
                                "items": {"type": "number"},
                                "minItems": 2,
                                "maxItems": 2
                            }
                        },
                        "max_iterations": {
                            "type": "integer",
                            "description": "Maximum optimization iterations (default: 150)",
                            "default": 150
                        },
                        "method": {
                            "type": "string",
                            "description": "Optimization method: 'Nelder-Mead' or 'Powell'",
                            "default": "Nelder-Mead"
                        }
                    },
                    "required": ["script_path", "target_image", "calibration_file", "output_dir", "param_bounds"]
                }
            ),
            Tool(
                name="poll_optimization",
                description=(
                    "Check the status of a running optimization task. "
                    "Returns current iteration, SSE, and whether complete."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "string",
                            "description": "Task ID from run_optimization"
                        }
                    },
                    "required": ["task_id"]
                }
            ),
            Tool(
                name="get_optimization_result",
                description=(
                    "Get the final result of a completed optimization task. "
                    "Returns best parameters, final SSE, and improvement percentage."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "string",
                            "description": "Task ID from run_optimization"
                        }
                    },
                    "required": ["task_id"]
                }
            ),
            Tool(
                name="apply_parameters",
                description=(
                    "Apply optimized parameters to a GDSFactory script and generate "
                    "a new GDS file. Returns paths to the modified script and GDS."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "script_path": {
                            "type": "string",
                            "description": "Path to the original GDSFactory script"
                        },
                        "params": {
                            "type": "object",
                            "description": "Dict of parameter name to new value",
                            "additionalProperties": {"type": "number"}
                        },
                        "output_dir": {
                            "type": "string",
                            "description": "Directory for output files"
                        }
                    },
                    "required": ["script_path", "params", "output_dir"]
                }
            ),
            # Calibration prep tools
            Tool(
                name="prepare_calibration",
                description=(
                    "Generate calibration.json from target image and footprint. "
                    "Maps between physical coordinates (microns) and pixel coordinates "
                    "for SSE comparison. Required before running JEE optimization."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "target_image": {
                            "type": "string",
                            "description": "Path to target B&W device image (device_bw.png)"
                        },
                        "footprint_json": {
                            "type": "string",
                            "description": "Path to footprint.json with device dimensions"
                        },
                        "output_path": {
                            "type": "string",
                            "description": "Path to save calibration.json"
                        }
                    },
                    "required": ["target_image", "footprint_json", "output_path"]
                }
            ),
            Tool(
                name="get_optimization_config",
                description=(
                    "Get default JEE optimization configuration with all available options. "
                    "Returns documented settings for max_iterations, method, footprint penalty, etc."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            # Explorer tools
            Tool(
                name="run_exploration",
                description=(
                    "Run two-phase optimization: grid search followed by parallel "
                    "Powell and Nelder-Mead from top N grid points. Returns the best "
                    "result across all methods. This is a long-running operation."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "script_path": {
                            "type": "string",
                            "description": "Path to the GDSFactory Python script"
                        },
                        "target_image": {
                            "type": "string",
                            "description": "Path to target image (PNG)"
                        },
                        "calibration_file": {
                            "type": "string",
                            "description": "Path to calibration.json"
                        },
                        "output_dir": {
                            "type": "string",
                            "description": "Directory for exploration outputs"
                        },
                        "param_values": {
                            "type": "object",
                            "description": "Optional dict mapping param name to list of values for grid search",
                            "additionalProperties": {
                                "type": "array",
                                "items": {"type": "number"}
                            }
                        },
                        "grid_points_per_param": {
                            "type": "integer",
                            "description": "Number of grid values per parameter (default: 5)",
                            "default": 5
                        },
                        "top_n_for_optimization": {
                            "type": "integer",
                            "description": "Number of top grid points to optimize from (default: 3)",
                            "default": 3
                        },
                        "max_iterations_per_method": {
                            "type": "integer",
                            "description": "Max iterations per optimization run (default: 100)",
                            "default": 100
                        },
                        "parallel_workers": {
                            "type": "integer",
                            "description": "Number of parallel optimization workers (default: 4)",
                            "default": 4
                        }
                    },
                    "required": ["script_path", "target_image", "calibration_file", "output_dir"]
                }
            ),
            Tool(
                name="poll_exploration",
                description="Check the status of a running exploration task.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "string",
                            "description": "Task ID from run_exploration"
                        }
                    },
                    "required": ["task_id"]
                }
            ),
            Tool(
                name="get_exploration_result",
                description=(
                    "Get completed exploration results with comparison of all methods. "
                    "Shows which optimizer (Powell or Nelder-Mead) achieved best results."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "string",
                            "description": "Task ID from run_exploration"
                        }
                    },
                    "required": ["task_id"]
                }
            )
        ]

    async def handle_tool(self, name: str, arguments: Dict[str, Any]) -> List[TextContent]:
        """Dispatch tool calls to handlers."""
        handlers = {
            "extract_parameters": self._extract_parameters,
            "compute_sse": self._compute_sse,
            "run_optimization": self._run_optimization,
            "poll_optimization": self._poll_optimization,
            "get_optimization_result": self._get_optimization_result,
            "apply_parameters": self._apply_parameters,
            "prepare_calibration": self._prepare_calibration,
            "get_optimization_config": self._get_optimization_config,
            # Explorer tools
            "run_exploration": self._run_exploration,
            "poll_exploration": self._poll_optimization,  # Reuse existing poll
            "get_exploration_result": self._get_optimization_result,  # Reuse existing
        }

        handler = handlers.get(name)
        if not handler:
            return [TextContent(
                type="text",
                text=serialize_result({"status": "error", "error": f"Unknown tool: {name}"})
            )]

        return await handler(arguments)

    @tool_handler
    async def _extract_parameters(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Extract parameters from a GDSFactory script using homi.jee_integration."""
        script_path = Path(args["script_path"])

        if not script_path.exists():
            return {"status": "error", "error": f"Script not found: {script_path}"}

        try:
            from homi.jee_integration import extract_factory_and_params

            loop = asyncio.get_event_loop()
            factory_fn, param_names, param_bounds, baseline, int_params = await loop.run_in_executor(
                _executor,
                lambda: extract_factory_and_params(script_path)
            )

            # Format for response
            params = [
                {
                    "name": name,
                    "value": baseline[name],
                    "bounds": list(param_bounds[name])
                }
                for name in param_names
            ]

            return {
                "status": "success",
                "script_path": str(script_path),
                "parameters": params,
                "count": len(params)
            }

        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to extract parameters: {e}",
                "script_path": str(script_path)
            }

    @tool_handler
    async def _compute_sse(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Compute SSE between target and raster images."""
        target_path = Path(args["target_image"])
        raster_path = Path(args["raster_image"])
        white_threshold = args.get("white_threshold", 245)

        if not target_path.exists():
            return {"status": "error", "error": f"Target image not found: {target_path}"}
        if not raster_path.exists():
            return {"status": "error", "error": f"Raster image not found: {raster_path}"}

        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        metrics = await loop.run_in_executor(
            _executor,
            lambda: sse_mod.compute_sse_metrics(target_path, raster_path, white_threshold)
        )

        return {
            "status": "success",
            **metrics
        }

    @tool_handler
    async def _run_optimization(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Start an optimization run using homi.jee_integration."""
        script_path = Path(args["script_path"])
        target_image = Path(args["target_image"])
        calibration_file = Path(args["calibration_file"])
        output_dir = Path(args["output_dir"])

        # Validate paths
        if not script_path.exists():
            return {"status": "error", "error": f"Script not found: {script_path}"}
        if not target_image.exists():
            return {"status": "error", "error": f"Target image not found: {target_image}"}
        if not calibration_file.exists():
            return {"status": "error", "error": f"Calibration file not found: {calibration_file}"}

        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)

        # Create task
        task_id = self.create_task("Running JEE optimization...")

        # Start optimization in background using integration layer
        async def run_opt():
            from homi.jee_integration import run_jee_optimization, get_jee_default_config

            # Build config from defaults + args
            config = get_jee_default_config()
            if "max_iterations" in args:
                config["max_iterations"] = args["max_iterations"]
            if "method" in args:
                config["method"] = args["method"]
            if "config" in args:
                config.update(args["config"])

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                _executor,
                lambda: run_jee_optimization(
                    script_path=script_path,
                    target_image_path=target_image,
                    calibration_path=calibration_file,
                    output_dir=output_dir,
                    config=config
                )
            )
            return result

        self.start_background_task(task_id, run_opt())

        return {
            "status": "started",
            "task_id": task_id,
            "message": "Optimization started. Use poll_optimization to check progress."
        }

    @tool_handler
    async def _poll_optimization(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Poll optimization task status."""
        task_id = args["task_id"]
        task = self.get_task(task_id)

        if task is None:
            return {"status": "error", "error": f"Unknown task: {task_id}"}

        return {
            "status": task.status.value,
            "progress": task.progress,
            "message": task.message,
            "task_id": task_id
        }

    @tool_handler
    async def _get_optimization_result(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get completed optimization result."""
        task_id = args["task_id"]
        task = self.get_task(task_id)

        if task is None:
            return {"status": "error", "error": f"Unknown task: {task_id}"}

        if task.status == TaskStatus.RUNNING:
            return {
                "status": "running",
                "message": "Optimization still in progress",
                "task_id": task_id
            }

        if task.status == TaskStatus.FAILED:
            return {
                "status": "failed",
                "error": task.error,
                "task_id": task_id
            }

        if task.status == TaskStatus.COMPLETED:
            return {
                "status": "completed",
                "result": task.result,
                "task_id": task_id
            }

        return {"status": task.status.value, "task_id": task_id}

    @tool_handler
    async def _apply_parameters(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Apply parameters to script and generate GDS."""
        script_path = Path(args["script_path"])
        params = args["params"]
        output_dir = Path(args["output_dir"])

        if not script_path.exists():
            return {"status": "error", "error": f"Script not found: {script_path}"}

        output_dir.mkdir(parents=True, exist_ok=True)

        # Read original script
        source = script_path.read_text()

        # Replace parameter values (simple regex-based replacement)
        modified_source = source
        for param_name, new_value in params.items():
            # Pattern: param_name = old_value
            pattern = rf'({param_name}\s*=\s*)[\d.]+'
            replacement = rf'\g<1>{new_value}'
            modified_source = re.sub(pattern, replacement, modified_source)

        # Write modified script
        new_script_path = output_dir / f"{script_path.stem}_optimized.py"
        new_script_path.write_text(modified_source)

        # Execute to generate GDS
        try:
            exec_globals = {}
            exec(modified_source, exec_globals)

            # Find and call the component factory
            component = None
            for name, obj in exec_globals.items():
                if hasattr(obj, "write_gds"):  # It's a gf.Component
                    component = obj
                    break

            if component is None:
                # Try to find and call a factory function
                for name, obj in exec_globals.items():
                    if callable(obj) and "component" in name.lower():
                        component = obj(**params)
                        break

            if component is not None:
                gds_path = output_dir / f"{script_path.stem}_optimized.gds"
                component.write_gds(str(gds_path))

                return {
                    "status": "success",
                    "script_path": str(new_script_path),
                    "gds_path": str(gds_path),
                    "applied_params": params
                }

        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to generate GDS: {e}",
                "script_path": str(new_script_path)
            }

        return {
            "status": "partial",
            "script_path": str(new_script_path),
            "message": "Script modified but GDS generation failed",
            "applied_params": params
        }

    @tool_handler
    async def _prepare_calibration(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Generate calibration.json from target image and footprint."""
        target_image = Path(args["target_image"])
        footprint_json = Path(args["footprint_json"])
        output_path = Path(args["output_path"])

        if not target_image.exists():
            return {"status": "error", "error": f"Target image not found: {target_image}"}
        if not footprint_json.exists():
            return {"status": "error", "error": f"Footprint JSON not found: {footprint_json}"}

        # Create output directory if needed
        output_path.parent.mkdir(parents=True, exist_ok=True)

        loop = asyncio.get_event_loop()

        def prepare():
            from homi.jee_integration import prepare_calibration
            result_path = prepare_calibration(
                target_image_path=target_image,
                footprint_json_path=footprint_json,
                output_path=output_path
            )
            return str(result_path)

        result_path = await loop.run_in_executor(_executor, prepare)

        # Read calibration to return contents
        with open(result_path) as f:
            calibration = json.load(f)

        return {
            "status": "success",
            "calibration_path": result_path,
            "calibration": calibration
        }

    @tool_handler
    async def _get_optimization_config(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get default JEE optimization configuration."""
        loop = asyncio.get_event_loop()

        def get_config():
            from homi.jee_integration import get_jee_default_config
            return get_jee_default_config()

        config = await loop.run_in_executor(_executor, get_config)

        # Add documentation
        config_docs = {
            "max_iterations": "Maximum number of optimization iterations (default: 100)",
            "max_function_evals": "Maximum function evaluations (default: 200)",
            "method": "Optimization algorithm: 'Nelder-Mead', 'Powell', or 'COBYLA'",
            "footprint_penalty_enabled": "Whether to penalize designs exceeding footprint",
            "footprint_penalty_weight": "Weight of footprint penalty (default: 1.0)",
            "footprint_penalty_mode": "'match' penalizes any difference, 'contain' only penalizes exceeding"
        }

        return {
            "status": "success",
            "config": config,
            "documentation": config_docs
        }

    @tool_handler
    async def _run_exploration(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Start exploration: grid search + parallel Powell/Nelder-Mead."""
        script_path = Path(args["script_path"])
        target_image = Path(args["target_image"])
        calibration_file = Path(args["calibration_file"])
        output_dir = Path(args["output_dir"])

        # Validate paths
        if not script_path.exists():
            return {"status": "error", "error": f"Script not found: {script_path}"}
        if not target_image.exists():
            return {"status": "error", "error": f"Target image not found: {target_image}"}
        if not calibration_file.exists():
            return {"status": "error", "error": f"Calibration file not found: {calibration_file}"}

        output_dir.mkdir(parents=True, exist_ok=True)

        # Create task
        task_id = self.create_task("Running JEE exploration (grid search + parallel optimization)...")

        # Start exploration in background
        async def run_explore():
            from homi.jee_integration import run_jee_exploration

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                _executor,
                lambda: run_jee_exploration(
                    script_path=script_path,
                    target_image_path=target_image,
                    calibration_path=calibration_file,
                    output_dir=output_dir,
                    param_values=args.get("param_values"),
                    grid_points_per_param=args.get("grid_points_per_param", 5),
                    top_n=args.get("top_n_for_optimization", 3),
                    max_iterations=args.get("max_iterations_per_method", 100),
                    parallel_workers=args.get("parallel_workers", 4),
                )
            )
            return result

        self.start_background_task(task_id, run_explore())

        return {
            "status": "started",
            "task_id": task_id,
            "message": "Exploration started. Use poll_exploration to check progress."
        }


# Entry point
async def main():
    logging.basicConfig(level=logging.INFO)
    server = JEEServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
