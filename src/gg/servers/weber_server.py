"""
Weber MCP Server - Interactive Explorer Generation

Tools for analyzing GDSFactory scripts and generating interactive
Streamlit explorers with parameter sliders and component swapping.
"""

from __future__ import annotations

import asyncio
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp.types import TextContent, Tool

from .base import BaseMCPServer, serialize_result, tool_handler

logger = logging.getLogger(__name__)

# Thread pool for blocking operations
_executor = ThreadPoolExecutor(max_workers=2)

# Swappable component groups
SWAPPABLE_COMPONENTS = {
    "bends": ["bend_circular", "bend_euler", "bend_s"],
    "straights": ["straight", "taper"],
    "shapes": ["rectangle", "circle", "ellipse", "triangle"],
    "couplers": ["coupler", "coupler_ring", "coupler_full"],
    "mmi": ["mmi1x2", "mmi2x2", "mmi_90degree_hybrid"],
}


class WeberServer(BaseMCPServer):
    """
    MCP Server for Weber (Interactive Explorer Generation).

    Provides tools for:
    - Analyzing GDSFactory scripts to extract parameters and components
    - Detecting swappable components
    - Generating interactive Streamlit explorers
    - Validating generated explorers
    """

    server_name = "homi-weber"
    server_version = "0.1.0"

    def get_tools(self) -> List[Tool]:
        return [
            Tool(
                name="analyze_script",
                description=(
                    "Analyze a GDSFactory Python script using AST parsing. "
                    "Extracts components, parameters, layers, and function structure."
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
                name="detect_swappable_components",
                description=(
                    "Identify components that can be swapped for alternatives. "
                    "For example, bend_circular can be swapped for bend_euler."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "analysis": {
                            "type": "object",
                            "description": "Analysis result from analyze_script"
                        }
                    },
                    "required": ["analysis"]
                }
            ),
            Tool(
                name="generate_slot_definitions",
                description=(
                    "Generate semantic slot definitions for grouping parameters. "
                    "Groups related parameters (e.g., all ring parameters together)."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "analysis": {
                            "type": "object",
                            "description": "Analysis result from analyze_script"
                        },
                        "output_path": {
                            "type": "string",
                            "description": "Path to save slot_definitions.py"
                        }
                    },
                    "required": ["analysis", "output_path"]
                }
            ),
            Tool(
                name="validate_explorer",
                description=(
                    "Validate a generated explorer for syntax errors and import issues."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "app_path": {
                            "type": "string",
                            "description": "Path to the explorer app.py"
                        }
                    },
                    "required": ["app_path"]
                }
            ),
            Tool(
                name="get_parameter_suggestions",
                description=(
                    "Get suggested slider ranges for parameters based on their values "
                    "and common photonics design patterns."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "parameters": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "value": {"type": "number"}
                                }
                            },
                            "description": "List of parameters with current values"
                        }
                    },
                    "required": ["parameters"]
                }
            ),
            # Device building tools from weber_integration
            Tool(
                name="build_device_with_params",
                description=(
                    "Execute a GDSFactory script with specific parameter values. "
                    "Injects slider values and returns the built component info. "
                    "Optionally saves the GDS to a file."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "script_source": {
                            "type": "string",
                            "description": "GDSFactory Python script source code"
                        },
                        "script_path": {
                            "type": "string",
                            "description": "Alternative: path to script file"
                        },
                        "params": {
                            "type": "object",
                            "description": "Dict mapping parameter name to value",
                            "additionalProperties": {"type": "number"}
                        },
                        "main_function": {
                            "type": "string",
                            "description": "Name of main function to call (auto-detected if not provided)"
                        },
                        "output_gds": {
                            "type": "string",
                            "description": "Optional path to save generated GDS"
                        }
                    },
                    "required": ["params"]
                }
            ),
            Tool(
                name="analyze_and_configure",
                description=(
                    "Analyze a GDSFactory script and generate slot configuration "
                    "using Weber's full analyzer. Returns analysis with parameter info "
                    "and slot configuration for UI rendering."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "script_source": {
                            "type": "string",
                            "description": "GDSFactory Python script source code"
                        },
                        "script_path": {
                            "type": "string",
                            "description": "Alternative: path to script file"
                        }
                    },
                    "required": []
                }
            ),
            Tool(
                name="build_component_map",
                description=(
                    "Build a component map from slot configuration. "
                    "Maps slot IDs to component IDs for swapping."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "slot_config": {
                            "type": "object",
                            "description": "SlotConfig from analyze_and_configure"
                        }
                    },
                    "required": ["slot_config"]
                }
            ),
            Tool(
                name="build_device_slots_dict",
                description=(
                    "Build device slots dictionary for layer assignment UI. "
                    "Compatible with Weber's render_layer_assignments()."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "slot_config": {
                            "type": "object",
                            "description": "SlotConfig from analyze_and_configure"
                        }
                    },
                    "required": ["slot_config"]
                }
            )
        ]

    async def handle_tool(self, name: str, arguments: Dict[str, Any]) -> List[TextContent]:
        """Dispatch tool calls to handlers."""
        handlers = {
            "analyze_script": self._analyze_script,
            "detect_swappable_components": self._detect_swappable_components,
            "generate_slot_definitions": self._generate_slot_definitions,
            "validate_explorer": self._validate_explorer,
            "get_parameter_suggestions": self._get_parameter_suggestions,
            "build_device_with_params": self._build_device_with_params,
            "analyze_and_configure": self._analyze_and_configure,
            "build_component_map": self._build_component_map,
            "build_device_slots_dict": self._build_device_slots_dict,
        }

        handler = handlers.get(name)
        if not handler:
            return [TextContent(
                type="text",
                text=serialize_result({"status": "error", "error": f"Unknown tool: {name}"})
            )]

        return await handler(arguments)

    @tool_handler
    async def _analyze_script(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a GDSFactory script using Weber's analyzer."""
        script_path = Path(args["script_path"])

        if not script_path.exists():
            return {"status": "error", "error": f"Script not found: {script_path}"}

        loop = asyncio.get_event_loop()

        def analyze():
            from homi.weber_integration import analyze_and_configure

            source = script_path.read_text()
            analysis, slot_config = analyze_and_configure(source)

            return {
                "script_path": str(script_path),
                "main_function": analysis.main_function,
                "components": [
                    {"type": c.type, "name": c.id}
                    for c in analysis.components
                ],
                "parameters": [
                    {"name": p.name, "value": p.value, "type": p.context}
                    for p in analysis.parameters
                ],
                "functions": [
                    {"name": f.name, "parameters": [a["name"] for a in f.parameters]}
                    for f in analysis.functions
                ],
                "slot_config_available": True
            }

        try:
            analysis = await loop.run_in_executor(_executor, analyze)
            return {"status": "success", "analysis": analysis}
        except Exception as e:
            return {"status": "error", "error": f"Weber analysis failed: {e}"}

    @tool_handler
    async def _detect_swappable_components(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Detect swappable components."""
        analysis = args["analysis"]
        components = analysis.get("components", [])

        swappable = []
        for comp in components:
            comp_type = comp.get("type", "")
            for group_name, group_types in SWAPPABLE_COMPONENTS.items():
                if comp_type in group_types:
                    alternatives = [t for t in group_types if t != comp_type]
                    swappable.append({
                        "component": comp,
                        "group": group_name,
                        "current": comp_type,
                        "alternatives": alternatives
                    })
                    break

        return {
            "status": "success",
            "swappable": swappable,
            "count": len(swappable)
        }

    @tool_handler
    async def _generate_slot_definitions(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Generate slot definitions file."""
        analysis = args["analysis"]
        output_path = Path(args["output_path"])

        parameters = analysis.get("parameters", [])

        # Group parameters by common prefixes
        groups = {}
        for param in parameters:
            name = param.get("name", "")
            # Extract prefix (e.g., "ring_" from "ring_radius")
            if "_" in name:
                prefix = name.split("_")[0]
            else:
                prefix = "general"

            if prefix not in groups:
                groups[prefix] = []
            groups[prefix].append(param)

        # Generate slot definitions
        slot_defs = []
        for group_name, group_params in groups.items():
            slot_defs.append({
                "name": group_name,
                "label": group_name.replace("_", " ").title(),
                "parameters": [p["name"] for p in group_params]
            })

        # Write to file
        output_path.parent.mkdir(parents=True, exist_ok=True)

        content = f'''"""
Auto-generated slot definitions for Weber explorer.
"""

SLOT_DEFINITIONS = {json.dumps(slot_defs, indent=4)}

LAYER_GROUPS = [
    {{"name": "device", "layers": [(1, 0)], "label": "Device Layer"}},
    {{"name": "ports", "layers": [(2, 0)], "label": "Port Layer"}},
]

GLOBAL_PARAMETERS = []
'''
        output_path.write_text(content)

        return {
            "status": "success",
            "output_path": str(output_path),
            "slots": slot_defs,
            "groups_count": len(slot_defs)
        }

    @tool_handler
    async def _validate_explorer(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Validate generated explorer."""
        app_path = Path(args["app_path"])

        if not app_path.exists():
            return {"status": "error", "error": f"App not found: {app_path}"}

        loop = asyncio.get_event_loop()

        def validate():
            import ast
            import sys

            source = app_path.read_text()
            errors = []

            # Check syntax
            try:
                ast.parse(source)
            except SyntaxError as e:
                errors.append(f"Syntax error at line {e.lineno}: {e.msg}")

            # Check imports (basic)
            required_imports = ["gdsfactory"]
            for imp in required_imports:
                if imp not in source:
                    errors.append(f"Missing import: {imp}")

            return {
                "valid": len(errors) == 0,
                "errors": errors
            }

        result = await loop.run_in_executor(_executor, validate)

        return {
            "status": "success" if result["valid"] else "invalid",
            "app_path": str(app_path),
            **result
        }

    @tool_handler
    async def _get_parameter_suggestions(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get suggested ranges for parameters using Weber's analysis."""
        script_source = args.get("script_source")
        script_path = args.get("script_path")

        if not script_source and not script_path:
            return {"status": "error", "error": "Either script_source or script_path required"}

        loop = asyncio.get_event_loop()

        def get_suggestions():
            from homi.weber_integration import analyze_and_configure, get_parameter_info_for_ui

            # Get script source
            if script_source:
                source = script_source
            else:
                source = Path(script_path).read_text()

            # Analyze with Weber to get smart parameter ranges
            analysis, slot_config = analyze_and_configure(source)
            params = get_parameter_info_for_ui(slot_config)

            # Format for response
            return [
                {
                    "name": p["name"],
                    "value": p["default_value"],
                    "suggested_min": p["min_value"],
                    "suggested_max": p["max_value"],
                    "step": p["step"],
                    "unit": p["unit"],
                    "label": p["label"],
                    "category": p["category"]
                }
                for p in params
            ]

        try:
            suggestions = await loop.run_in_executor(_executor, get_suggestions)
            return {
                "status": "success",
                "suggestions": suggestions,
                "count": len(suggestions)
            }
        except Exception as e:
            return {"status": "error", "error": f"Failed to get parameter suggestions: {e}"}

    @tool_handler
    async def _build_device_with_params(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Build device with specific parameter values."""
        params = args["params"]
        script_source = args.get("script_source")
        script_path = args.get("script_path")
        main_function = args.get("main_function")
        output_gds = args.get("output_gds")

        # Get script source
        if script_source is None:
            if script_path:
                script_path = Path(script_path)
                if not script_path.exists():
                    return {"status": "error", "error": f"Script not found: {script_path}"}
                script_source = script_path.read_text()
            else:
                return {"status": "error", "error": "Must provide script_source or script_path"}

        loop = asyncio.get_event_loop()

        def build():
            from homi.weber_integration import build_device_with_params
            component = build_device_with_params(
                script_source=script_source,
                slider_values=params,
                main_function=main_function
            )

            result = {
                "name": component.name,
                "size": list(component.size),
                "ports": [p.name for p in component.ports],
            }

            # Save GDS if requested
            if output_gds:
                output_path = Path(output_gds)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                component.write_gds(str(output_path))
                result["gds_path"] = str(output_path)

            return result

        try:
            result = await loop.run_in_executor(_executor, build)
            return {"status": "success", **result}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    @tool_handler
    async def _analyze_and_configure(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze script and generate slot configuration."""
        script_source = args.get("script_source")
        script_path = args.get("script_path")

        # Get script source
        if script_source is None:
            if script_path:
                script_path = Path(script_path)
                if not script_path.exists():
                    return {"status": "error", "error": f"Script not found: {script_path}"}
                script_source = script_path.read_text()
            else:
                return {"status": "error", "error": "Must provide script_source or script_path"}

        loop = asyncio.get_event_loop()

        def analyze():
            from homi.weber_integration import analyze_and_configure, get_parameter_info_for_ui

            analysis, slot_config = analyze_and_configure(script_source)

            # Convert to serializable format
            params = get_parameter_info_for_ui(slot_config)

            return {
                "analysis": {
                    "main_function": analysis.main_function,
                    "functions": [f.name for f in analysis.functions],
                    "parameters": [{"name": p.name, "value": p.value} for p in analysis.parameters],
                    "components": [{"type": c.type, "variable": c.id} for c in analysis.components],
                },
                "slot_config": {
                    "slots": [
                        {
                            "slot_id": s.slot_id,
                            "display_name": s.display_name,
                            "category": s.category,
                            "component_ids": s.component_ids,
                            "current_type": s.current_type,
                            "allowed_types": s.allowed_types,
                            "parameters": [
                                {
                                    "name": p.name,
                                    "label": p.label,
                                    "min_value": p.min_value,
                                    "max_value": p.max_value,
                                    "default_value": p.default_value,
                                    "step": p.step,
                                    "unit": p.unit,
                                }
                                for p in s.parameters
                            ],
                        }
                        for s in slot_config.slots
                    ]
                },
                "parameters_for_ui": params
            }

        try:
            result = await loop.run_in_executor(_executor, analyze)
            return {"status": "success", **result}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    @tool_handler
    async def _build_component_map(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Build component map from slot configuration."""
        slot_config = args["slot_config"]

        # Build map from slot_config dict
        component_map = {}
        for slot in slot_config.get("slots", []):
            component_map[slot["slot_id"]] = slot.get("component_ids", [])

        return {
            "status": "success",
            "component_map": component_map
        }

    @tool_handler
    async def _build_device_slots_dict(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Build device slots dictionary for layer assignment UI."""
        slot_config = args["slot_config"]

        # Build slots dict from slot_config
        device_slots = {}
        for slot in slot_config.get("slots", []):
            device_slots[slot["slot_id"]] = {
                "display_name": slot.get("display_name", slot["slot_id"]),
                "component_ids": slot.get("component_ids", []),
                "current_type": slot.get("current_type"),
                "allowed_types": slot.get("allowed_types", []),
                "category": slot.get("category", "general"),
                "parameters": slot.get("parameters", []),
                "layer_group": slot.get("layer_group"),
            }

        return {
            "status": "success",
            "device_slots": device_slots
        }


# Entry point
async def main():
    logging.basicConfig(level=logging.INFO)
    server = WeberServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
