"""
Michaelangelo MCP Server - GDS Generation from Device Images

Tools for converting B&W device images into parametric GDSFactory scripts
using multi-turn conversations with seed exploration and iterative refinement.

Supports 54 vision-language models across 6 providers:
- Google Gemini (5 models) - Direct API
- Anthropic Claude (9 models) - Direct API
- OpenAI GPT (10 models) - Direct API
- Meta Llama (4 models) - OpenRouter
- Moonshot Kimi (4 models) - OpenRouter
- Alibaba Qwen-VL (22 models) - OpenRouter
"""

from __future__ import annotations

import asyncio
import json
import logging
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List

from mcp.types import TextContent, Tool

import michaelangelo

from .base import BaseMCPServer, serialize_result, tool_handler

logger = logging.getLogger(__name__)

# Thread pool for blocking operations
_executor = ThreadPoolExecutor(max_workers=2)

# Generation presets
GENERATION_PRESETS = {
    "quick": {
        "seed_range": 2,
        "additional_turns": 2,
        "num_parallel": 4,
        "description": "Fast exploration, ~5 minutes"
    },
    "balanced": {
        "seed_range": 6,
        "additional_turns": 3,
        "num_parallel": 8,
        "description": "Good balance, ~10 minutes"
    },
    "thorough": {
        "seed_range": 12,
        "additional_turns": 5,
        "num_parallel": 8,
        "description": "Comprehensive, ~20 minutes"
    },
    "maximum": {
        "seed_range": 20,
        "additional_turns": 8,
        "num_parallel": 12,
        "description": "Maximum exploration, ~40 minutes"
    }
}


class MichelangeloServer(BaseMCPServer):
    """
    MCP Server for Michaelangelo (GDS Generation).

    Provides tools for:
    - Setting up component directories with proper structure
    - Running calibration for image-to-physical space mapping
    - Running Phase 1 multi-seed exploration
    - Running Phase 2 extended iteration
    - Getting generation results and metrics
    """

    server_name = "homi-michaelangelo"
    server_version = "0.1.0"

    def get_tools(self) -> List[Tool]:
        return [
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
                    "Required before running GDS generation."
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
            Tool(
                name="start_phase1_exploration",
                description=(
                    "Start Phase 1 multi-seed GDS generation. Tests multiple seeds in parallel, "
                    "each with 2 turns of generation and refinement. Returns task_id for polling. "
                    "Supports 54 models across Gemini, Claude, OpenAI, Llama, Kimi, and Qwen."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "component_dir": {
                            "type": "string",
                            "description": "Path to component directory"
                        },
                        "preset": {
                            "type": "string",
                            "enum": ["quick", "balanced", "thorough", "maximum"],
                            "description": "Generation preset (default: balanced)",
                            "default": "balanced"
                        },
                        "base_seed": {
                            "type": "integer",
                            "description": "Base seed for exploration (default: 1333)",
                            "default": 1333
                        },
                        "model": {
                            "type": "string",
                            "description": (
                                "Model to use in unified format: provider/model-name. "
                                "Examples: gemini/gemini-3-flash-preview (default), "
                                "anthropic/claude-sonnet-4.5, openai/gpt-5.2, "
                                "qwen/qwen3-vl-235b-a22b-thinking, meta-llama/llama-4-maverick"
                            ),
                            "default": "gemini/gemini-3-flash-preview"
                        }
                    },
                    "required": ["component_dir"]
                }
            ),
            Tool(
                name="poll_generation_status",
                description=(
                    "Check the status of a running generation task. "
                    "Returns progress percentage and current seed being processed."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "string",
                            "description": "Task ID from start_phase1_exploration or start_phase2_iteration"
                        }
                    },
                    "required": ["task_id"]
                }
            ),
            Tool(
                name="get_phase1_results",
                description=(
                    "Get results from Phase 1 exploration. Returns ranked list of seeds "
                    "with their IoU/Dice scores and paths to generated files."
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
            Tool(
                name="start_phase2_iteration",
                description=(
                    "Start Phase 2 extended iteration on selected seeds from Phase 1. "
                    "Continues refining the best seeds for additional turns. "
                    "Supports 54 models across Gemini, Claude, OpenAI, Llama, Kimi, and Qwen."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "component_dir": {
                            "type": "string",
                            "description": "Path to component directory"
                        },
                        "seeds": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "description": "Seeds to continue (from Phase 1 results)"
                        },
                        "additional_turns": {
                            "type": "integer",
                            "description": "Number of additional turns (default: 3)",
                            "default": 3
                        },
                        "iou_threshold": {
                            "type": "number",
                            "description": "Minimum IoU to continue (default: 0.0)",
                            "default": 0.0
                        },
                        "model": {
                            "type": "string",
                            "description": (
                                "Model to use in unified format: provider/model-name. "
                                "Examples: gemini/gemini-3-flash-preview (default), "
                                "anthropic/claude-sonnet-4.5, openai/gpt-5.2, "
                                "qwen/qwen3-vl-235b-a22b-thinking, meta-llama/llama-4-maverick"
                            ),
                            "default": "gemini/gemini-3-flash-preview"
                        }
                    },
                    "required": ["component_dir", "seeds"]
                }
            ),
            Tool(
                name="get_phase2_results",
                description=(
                    "Get final results from Phase 2. Returns the best result with "
                    "paths to GDS file, script, and visualization images."
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
            Tool(
                name="get_generation_metrics",
                description=(
                    "Get detailed metrics and visualizations from generation. "
                    "Returns IoU/Dice for all seeds, diff images, and rasters."
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
            Tool(
                name="list_presets",
                description="List available generation presets with their configurations.",
                inputSchema={
                    "type": "object",
                    "properties": {}
                }
            ),
            Tool(
                name="list_available_models",
                description=(
                    "List all available models for GDS generation. "
                    "Supports 54 models across 6 providers: Gemini, Claude, OpenAI, Llama, Kimi, Qwen."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "provider": {
                            "type": "string",
                            "enum": ["gemini", "claude", "openai", "openrouter"],
                            "description": "Filter by provider (optional)"
                        }
                    }
                }
            )
        ]

    async def handle_tool(self, name: str, arguments: Dict[str, Any]) -> List[TextContent]:
        """Dispatch tool calls to handlers."""
        handlers = {
            "setup_component_directory": self._setup_component_directory,
            "run_calibration": self._run_calibration,
            "start_phase1_exploration": self._start_phase1_exploration,
            "poll_generation_status": self._poll_generation_status,
            "get_phase1_results": self._get_phase1_results,
            "start_phase2_iteration": self._start_phase2_iteration,
            "get_phase2_results": self._get_phase2_results,
            "get_generation_metrics": self._get_generation_metrics,
            "list_presets": self._list_presets,
            "list_available_models": self._list_available_models,
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

        # Create default prompts if they don't exist
        prompt_path = output_dir / "prompt.md"
        if not prompt_path.exists():
            prompt_path.write_text("""Generate a GDSFactory Python script that recreates the device shown in this image.

Requirements:
- Use gdsfactory library (import gdsfactory as gf)
- Create a parametric function that returns a gf.Component
- Match the geometry as closely as possible
- Use appropriate layer (1, 0) for the main device
- Save the GDS file at the end

The image shows a black silhouette of the device on white background.
""")

        iteration_prompt_path = output_dir / "iteration_prompt.md"
        if not iteration_prompt_path.exists():
            iteration_prompt_path.write_text("""Here is your previous attempt rasterized as an image.

Compare it to the original target and improve the code:
- Fix any geometry mismatches
- Adjust dimensions to better match
- Ensure all features are captured

Provide an improved version of the GDSFactory script.
""")

        return {
            "status": "success",
            "component_dir": str(output_dir),
            "files_created": [
                str(component_image),
                str(footprint_path),
                str(prompt_path),
                str(iteration_prompt_path)
            ],
            "footprint_um": footprint_data["footprint_um"]
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
                "calibration": calibration
            }

        except Exception as e:
            return {"status": "error", "error": f"Calibration failed: {e}"}

    @tool_handler
    async def _start_phase1_exploration(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Start Phase 1 multi-seed exploration."""
        component_dir = Path(args["component_dir"])
        preset_name = args.get("preset", "balanced")
        base_seed = args.get("base_seed", 1333)
        model = args.get("model", "gemini-3-flash-preview")

        # Validate component directory
        required_files = ["component.png", "footprint.json", "calibration.json"]
        for fname in required_files:
            if not (component_dir / fname).exists():
                return {"status": "error", "error": f"{fname} not found in {component_dir}"}

        preset = GENERATION_PRESETS.get(preset_name)
        if not preset:
            return {"status": "error", "error": f"Unknown preset: {preset_name}"}

        # Create task
        task_id = self.create_task(f"Phase 1 exploration ({preset_name} preset)")

        # Start background task
        async def run_phase1():
            # This would call the actual phase1 script
            # For now, return a placeholder
            loop = asyncio.get_event_loop()

            def run():
                import subprocess

                phase1_script = Path(michaelangelo.__file__).parent / "core" / "gemini_multiturn_seed_exploration.py"

                if not phase1_script.exists():
                    return {"error": f"Phase 1 script not found: {phase1_script}"}

                cmd = [
                    sys.executable, str(phase1_script),
                    "--component-dir", str(component_dir),
                    "--base-seed", str(base_seed),
                    "--seed-range", str(preset["seed_range"]),
                    "--num-parallel", str(preset["num_parallel"]),
                    "--model", model
                ]

                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)

                    # Read results
                    results_path = component_dir / "results" / "multiturn_seeds" / "exploration_summary.json"
                    if results_path.exists():
                        with open(results_path) as f:
                            return json.load(f)
                    else:
                        return {"error": "No results generated", "stdout": result.stdout, "stderr": result.stderr}

                except subprocess.TimeoutExpired:
                    return {"error": "Phase 1 timed out"}
                except Exception as e:
                    return {"error": str(e)}

            return await loop.run_in_executor(_executor, run)

        self.start_background_task(task_id, run_phase1())

        return {
            "status": "started",
            "task_id": task_id,
            "preset": preset_name,
            "preset_config": preset,
            "message": f"Phase 1 exploration started with {preset_name} preset. Use poll_generation_status to check progress."
        }

    @tool_handler
    async def _poll_generation_status(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Poll generation task status."""
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
    async def _get_phase1_results(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get Phase 1 exploration results."""
        component_dir = Path(args["component_dir"])
        results_path = component_dir / "results" / "multiturn_seeds" / "exploration_summary.json"

        if not results_path.exists():
            return {"status": "error", "error": "Phase 1 results not found. Run start_phase1_exploration first."}

        with open(results_path) as f:
            results = json.load(f)

        # Sort by IoU descending
        seed_results = results.get("seed_results", [])
        seed_results.sort(key=lambda x: x.get("turn2_metrics", {}).get("iou", 0), reverse=True)

        return {
            "status": "success",
            "total_seeds": len(seed_results),
            "seeds": [
                {
                    "seed": r["seed"],
                    "iou": r.get("turn2_metrics", {}).get("iou", 0),
                    "dice": r.get("turn2_metrics", {}).get("dice", 0),
                    "success": r.get("turn2_success", False)
                }
                for r in seed_results[:10]  # Top 10
            ],
            "best": seed_results[0] if seed_results else None
        }

    @tool_handler
    async def _start_phase2_iteration(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Start Phase 2 extended iteration."""
        component_dir = Path(args["component_dir"])
        seeds = args["seeds"]
        additional_turns = args.get("additional_turns", 3)
        model = args.get("model", "gemini-3-flash-preview")

        # Validate
        if not seeds:
            return {"status": "error", "error": "No seeds provided"}

        phase1_results = component_dir / "results" / "multiturn_seeds" / "exploration_summary.json"
        if not phase1_results.exists():
            return {"status": "error", "error": "Phase 1 results not found. Run Phase 1 first."}

        # Create task
        task_id = self.create_task(f"Phase 2 iteration ({len(seeds)} seeds)")

        async def run_phase2():
            loop = asyncio.get_event_loop()

            def run():
                import subprocess

                phase2_script = Path(michaelangelo.__file__).parent / "core" / "gemini_extended_iteration.py"

                if not phase2_script.exists():
                    return {"error": f"Phase 2 script not found: {phase2_script}"}

                cmd = [
                    sys.executable, str(phase2_script),
                    "--component-dir", str(component_dir),
                    "--phase1-dir", str(component_dir / "multiturn_seeds"),
                    "--additional-turns", str(additional_turns),
                    "--sse-threshold", "999999999",  # Allow all seeds - filtering done by MCP
                    "--model", model
                ]

                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)

                    results_path = component_dir / "results" / "extended_iteration" / "extended_exploration_summary.json"
                    if results_path.exists():
                        with open(results_path) as f:
                            return json.load(f)
                    else:
                        return {"error": "No results generated", "stdout": result.stdout, "stderr": result.stderr}

                except subprocess.TimeoutExpired:
                    return {"error": "Phase 2 timed out"}
                except Exception as e:
                    return {"error": str(e)}

            return await loop.run_in_executor(_executor, run)

        self.start_background_task(task_id, run_phase2())

        return {
            "status": "started",
            "task_id": task_id,
            "seeds": seeds,
            "additional_turns": additional_turns,
            "message": "Phase 2 iteration started. Use poll_generation_status to check progress."
        }

    @tool_handler
    async def _get_phase2_results(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get Phase 2 final results."""
        component_dir = Path(args["component_dir"])
        results_path = component_dir / "results" / "extended_iteration" / "extended_exploration_summary.json"

        if not results_path.exists():
            return {"status": "error", "error": "Phase 2 results not found."}

        with open(results_path) as f:
            results = json.load(f)

        # Find best result
        seed_results = results.get("seed_results", []) or results.get("results", [])
        if not seed_results:
            return {"status": "error", "error": "No successful results in Phase 2"}

        # Find best by IoU (prefer best_iou if available, fall back to final_iou)
        best = max(seed_results, key=lambda x: x.get("best_iou", x.get("final_iou", 0)))

        return {
            "status": "success",
            "best": {
                "seed": best.get("seed") or best.get("run_id"),
                "iou": best.get("best_iou", best.get("final_iou", 0)),
                "best_iou_turn": best.get("best_iou_turn"),
                "best_sse": best.get("best_sse", best.get("final_sse")),
                "best_sse_turn": best.get("best_sse_turn"),
                "turns_completed": best.get("turns_completed") or best.get("final_turn", 0),
                "script_path": best.get("best_script_path"),
                "gds_path": best.get("best_gds_path"),
                "raster_path": best.get("best_raster_path")
            },
            "all_results": [
                {
                    "seed": r.get("seed") or r.get("run_id"),
                    "iou": r.get("best_iou", r.get("final_iou", 0)),
                    "sse": r.get("best_sse", r.get("final_sse")),
                    "success": r.get("success", not r.get("early_stopped", False))
                }
                for r in seed_results
            ]
        }

    @tool_handler
    async def _get_generation_metrics(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed generation metrics."""
        component_dir = Path(args["component_dir"])

        metrics = {
            "status": "success",
            "component_dir": str(component_dir)
        }

        # Check Phase 1
        phase1_path = component_dir / "results" / "multiturn_seeds" / "exploration_summary.json"
        if phase1_path.exists():
            with open(phase1_path) as f:
                phase1 = json.load(f)
            metrics["phase1"] = {
                "completed": True,
                "total_seeds": len(phase1.get("seed_results", [])),
                "successful_seeds": sum(1 for r in phase1.get("seed_results", []) if r.get("turn2_success")),
                "best_iou": max((r.get("turn2_metrics", {}).get("iou", 0) for r in phase1.get("seed_results", [])), default=0)
            }
        else:
            metrics["phase1"] = {"completed": False}

        # Check Phase 2
        phase2_path = component_dir / "results" / "extended_iteration" / "extended_exploration_summary.json"
        if phase2_path.exists():
            with open(phase2_path) as f:
                phase2 = json.load(f)
            metrics["phase2"] = {
                "completed": True,
                "seeds_processed": len(phase2.get("seed_results", [])),
                "best_iou": max((r.get("final_iou", 0) for r in phase2.get("seed_results", [])), default=0)
            }
        else:
            metrics["phase2"] = {"completed": False}

        return metrics

    @tool_handler
    async def _list_presets(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """List available generation presets."""
        return {
            "status": "success",
            "presets": GENERATION_PRESETS
        }

    @tool_handler
    async def _list_available_models(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """List available models for GDS generation."""
        provider = args.get("provider")

        try:
            from homi.model_client import list_models, list_providers, get_model_capabilities

            models = list_models(provider)

            # Group by provider
            by_provider = {}
            for model in models:
                caps = get_model_capabilities(model)
                provider_name = model.split("/")[0]
                if provider_name not in by_provider:
                    by_provider[provider_name] = []
                by_provider[provider_name].append({
                    "name": model,
                    "supports_seed": caps.supports_seed if caps else False,
                    "supports_thinking": caps.supports_thinking if caps else False,
                })

            return {
                "status": "success",
                "total_models": len(models),
                "providers": list_providers(),
                "models_by_provider": by_provider,
                "all_models": models
            }
        except ImportError:
            return {
                "status": "error",
                "error": "model_client not available. Install homi package."
            }


# Entry point
async def main():
    logging.basicConfig(level=logging.INFO)
    server = MichelangeloServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
