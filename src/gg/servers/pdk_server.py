"""
PDK MCP Server - Foundry Process Mapping

Tools for mapping generic GDS designs to foundry-specific PDKs,
analyzing fabrication parameters from papers, and validating designs.

New in v0.2.0:
- parse_pdk_document: Parse foundry PDK PDF documents into structured definitions
- list_pdk_layers_full: List layers with complete material properties
- get_layer_material_properties: Get Tidy3D-ready material properties for simulation
- load_builtin_pdk: Load pre-defined PDKs (Lightium TFLN, HyperLight, etc.)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp.types import TextContent, Tool

from .base import BaseMCPServer, serialize_result, tool_handler

logger = logging.getLogger(__name__)

# Import PDK module for new functionality
try:
    from gg.pdk import (
        PDKDefinition,
        PDKParser,
        PDKTidy3DConverter,
        load_builtin_pdk,
        list_builtin_pdks,
        is_tidy3d_available,
    )
    PDK_MODULE_AVAILABLE = True
except ImportError:
    PDK_MODULE_AVAILABLE = False
    logger.warning("PDK module not available. Some features disabled.")

# Thread pool for blocking operations
_executor = ThreadPoolExecutor(max_workers=2)

# Available PDKs with their specifications
AVAILABLE_PDKS = {
    "generic_si220": {
        "name": "Generic Si 220nm",
        "description": "Generic silicon photonics, 220nm SOI",
        "process": {
            "waveguide_thickness_nm": 220,
            "box_thickness_um": 2.0,
            "cladding": "SiO2",
            "substrate": "Si"
        },
        "layers": {
            "waveguide": (1, 0),
            "slab": (2, 0),
            "heater": (10, 0),
            "metal": (40, 0)
        },
        "design_rules": {
            "min_waveguide_width_um": 0.4,
            "min_gap_um": 0.15,
            "min_bend_radius_um": 5.0
        },
        "wavelength_nm": 1550
    },
    "aim_photonics": {
        "name": "AIM Photonics",
        "description": "AIM Photonics foundry PDK",
        "process": {
            "waveguide_thickness_nm": 220,
            "box_thickness_um": 2.0,
            "cladding": "SiO2",
            "substrate": "Si"
        },
        "layers": {
            "WGCORE": (1, 0),
            "SLAB": (2, 0),
            "TRENCH": (3, 0),
            "HTR": (10, 0),
            "M1": (40, 0)
        },
        "design_rules": {
            "min_waveguide_width_um": 0.45,
            "min_gap_um": 0.2,
            "min_bend_radius_um": 5.0
        },
        "wavelength_nm": 1550
    },
    "amf": {
        "name": "AMF (Advanced Micro Foundry)",
        "description": "AMF Singapore foundry PDK",
        "process": {
            "waveguide_thickness_nm": 220,
            "box_thickness_um": 2.0,
            "cladding": "SiO2",
            "substrate": "Si"
        },
        "layers": {
            "Si_Full": (1, 0),
            "Si_Partial": (2, 0),
            "Heater": (10, 0),
            "Metal": (40, 0)
        },
        "design_rules": {
            "min_waveguide_width_um": 0.4,
            "min_gap_um": 0.15,
            "min_bend_radius_um": 5.0
        },
        "wavelength_nm": 1550
    },
    "sin": {
        "name": "Silicon Nitride",
        "description": "Generic SiN platform",
        "process": {
            "waveguide_thickness_nm": 400,
            "box_thickness_um": 3.0,
            "cladding": "SiO2",
            "substrate": "Si"
        },
        "layers": {
            "waveguide": (1, 0),
            "heater": (10, 0),
            "metal": (40, 0)
        },
        "design_rules": {
            "min_waveguide_width_um": 0.8,
            "min_gap_um": 0.3,
            "min_bend_radius_um": 20.0
        },
        "wavelength_nm": 1550
    }
}

# Common process keywords for matching
PROCESS_KEYWORDS = {
    "220nm": ["generic_si220", "aim_photonics", "amf"],
    "220 nm": ["generic_si220", "aim_photonics", "amf"],
    "silicon nitride": ["sin"],
    "SiN": ["sin"],
    "Si3N4": ["sin"],
    "SOI": ["generic_si220", "aim_photonics", "amf"],
    "1550nm": ["generic_si220", "aim_photonics", "amf", "sin"],
    "1550 nm": ["generic_si220", "aim_photonics", "amf", "sin"],
    "1310nm": ["generic_si220"],
    "AIM": ["aim_photonics"],
    "AMF": ["amf"],
}


class PDKServer(BaseMCPServer):
    """
    MCP Server for PDK (Foundry Process Mapping).

    Provides tools for:
    - Analyzing paper text to extract fabrication parameters
    - Matching designs to compatible PDKs
    - Mapping GDS layers to PDK-specific layers
    - Running design rule checks (DRC)
    """

    server_name = "homi-pdk"
    server_version = "0.2.0"  # Added PDK document parsing tools

    def __init__(self):
        super().__init__()
        self._genai_client = None

    def _get_genai_client(self):
        """Get or create Gemini client for text analysis."""
        if self._genai_client is None:
            from google import genai
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY environment variable not set")
            self._genai_client = genai.Client(api_key=api_key)
        return self._genai_client

    def get_tools(self) -> List[Tool]:
        return [
            Tool(
                name="analyze_paper_process",
                description=(
                    "Analyze paper text to extract fabrication process parameters. "
                    "Identifies waveguide thickness, materials, wavelength, and foundry hints."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "paper_text": {
                            "type": "string",
                            "description": "Text extracted from the paper (abstract, methods, etc.)"
                        },
                        "pdf_path": {
                            "type": "string",
                            "description": "Optional path to PDF for direct extraction"
                        }
                    },
                    "required": []
                }
            ),
            Tool(
                name="list_available_pdks",
                description="List all available PDKs with their specifications.",
                inputSchema={
                    "type": "object",
                    "properties": {}
                }
            ),
            Tool(
                name="match_pdk",
                description=(
                    "Find compatible PDKs for given process information. "
                    "Returns ranked matches with confidence scores."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "process_info": {
                            "type": "object",
                            "description": "Process info from analyze_paper_process",
                            "properties": {
                                "waveguide_thickness_nm": {"type": "number"},
                                "material": {"type": "string"},
                                "wavelength_nm": {"type": "number"},
                                "foundry_hint": {"type": "string"}
                            }
                        }
                    },
                    "required": ["process_info"]
                }
            ),
            Tool(
                name="get_pdk_layer_mapping",
                description=(
                    "Get layer mapping from generic layers to PDK-specific layers."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "pdk_name": {
                            "type": "string",
                            "description": "Name of the target PDK"
                        },
                        "source_layers": {
                            "type": "array",
                            "items": {
                                "type": "array",
                                "items": {"type": "integer"},
                                "minItems": 2,
                                "maxItems": 2
                            },
                            "description": "List of source layers as [layer, datatype] pairs"
                        }
                    },
                    "required": ["pdk_name"]
                }
            ),
            Tool(
                name="convert_to_pdk",
                description=(
                    "Convert a GDS file to use PDK-specific layers."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "gds_path": {
                            "type": "string",
                            "description": "Path to input GDS file"
                        },
                        "pdk_name": {
                            "type": "string",
                            "description": "Target PDK name"
                        },
                        "output_path": {
                            "type": "string",
                            "description": "Path for output GDS file"
                        },
                        "layer_mapping": {
                            "type": "object",
                            "description": "Optional custom layer mapping",
                            "additionalProperties": {
                                "type": "array",
                                "items": {"type": "integer"}
                            }
                        }
                    },
                    "required": ["gds_path", "pdk_name", "output_path"]
                }
            ),
            Tool(
                name="run_drc",
                description=(
                    "Run design rule check against PDK rules. "
                    "Returns list of violations with locations."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "gds_path": {
                            "type": "string",
                            "description": "Path to GDS file"
                        },
                        "pdk_name": {
                            "type": "string",
                            "description": "PDK to check against"
                        }
                    },
                    "required": ["gds_path", "pdk_name"]
                }
            ),
            Tool(
                name="suggest_drc_fixes",
                description=(
                    "Suggest fixes for DRC violations."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "violations": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "rule": {"type": "string"},
                                    "location": {"type": "object"},
                                    "value": {"type": "number"}
                                }
                            },
                            "description": "List of violations from run_drc"
                        }
                    },
                    "required": ["violations"]
                }
            ),
            # New PDK Document Parsing Tools
            Tool(
                name="parse_pdk_document",
                description=(
                    "Parse a foundry PDK PDF document to extract layer definitions, "
                    "material properties, cross-sections, and design rules. "
                    "Returns a structured PDK definition that can be used for layer assignment."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "pdf_path": {
                            "type": "string",
                            "description": "Path to the PDK PDF document"
                        },
                        "pdk_name": {
                            "type": "string",
                            "description": "Optional name to assign to the parsed PDK"
                        },
                        "save_path": {
                            "type": "string",
                            "description": "Optional path to save the parsed PDK as JSON"
                        }
                    },
                    "required": ["pdf_path"]
                }
            ),
            Tool(
                name="load_builtin_pdk",
                description=(
                    "Load a pre-defined builtin PDK. Available: lightium_tfln, hyperlight_active, generic_si220."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "pdk_name": {
                            "type": "string",
                            "description": "Name of builtin PDK (lightium_tfln, hyperlight_active, generic_si220)"
                        }
                    },
                    "required": ["pdk_name"]
                }
            ),
            Tool(
                name="list_pdk_layers_full",
                description=(
                    "List all layers in a PDK with complete material and geometry properties. "
                    "Use after parse_pdk_document or load_builtin_pdk."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "pdk_name": {
                            "type": "string",
                            "description": "Name of the PDK to list layers from"
                        }
                    },
                    "required": ["pdk_name"]
                }
            ),
            Tool(
                name="get_layer_material_properties",
                description=(
                    "Get Tidy3D-compatible material properties for a specific PDK layer. "
                    "Returns refractive indices and material type for simulation."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "pdk_name": {
                            "type": "string",
                            "description": "Name of the PDK"
                        },
                        "layer_name": {
                            "type": "string",
                            "description": "Name of the layer to get material for"
                        }
                    },
                    "required": ["pdk_name", "layer_name"]
                }
            ),
            Tool(
                name="get_pdk_cross_sections",
                description=(
                    "Get waveguide cross-section definitions from a PDK. "
                    "Returns film thickness, etch depth, slab thickness, and sidewall angles."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "pdk_name": {
                            "type": "string",
                            "description": "Name of the PDK"
                        }
                    },
                    "required": ["pdk_name"]
                }
            )
        ]

    async def handle_tool(self, name: str, arguments: Dict[str, Any]) -> List[TextContent]:
        """Dispatch tool calls to handlers."""
        handlers = {
            "analyze_paper_process": self._analyze_paper_process,
            "list_available_pdks": self._list_available_pdks,
            "match_pdk": self._match_pdk,
            "get_pdk_layer_mapping": self._get_pdk_layer_mapping,
            "convert_to_pdk": self._convert_to_pdk,
            "run_drc": self._run_drc,
            "suggest_drc_fixes": self._suggest_drc_fixes,
            # New PDK document parsing handlers
            "parse_pdk_document": self._parse_pdk_document,
            "load_builtin_pdk": self._load_builtin_pdk,
            "list_pdk_layers_full": self._list_pdk_layers_full,
            "get_layer_material_properties": self._get_layer_material_properties,
            "get_pdk_cross_sections": self._get_pdk_cross_sections,
        }

        handler = handlers.get(name)
        if not handler:
            return [TextContent(
                type="text",
                text=serialize_result({"status": "error", "error": f"Unknown tool: {name}"})
            )]

        return await handler(arguments)

    @tool_handler
    async def _analyze_paper_process(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze paper to extract process info."""
        paper_text = args.get("paper_text", "")
        pdf_path = args.get("pdf_path")

        # Extract text from PDF if provided
        if pdf_path and not paper_text:
            loop = asyncio.get_event_loop()

            def extract_text():
                import fitz
                doc = fitz.open(pdf_path)
                text = ""
                for page_num in range(min(10, len(doc))):  # First 10 pages
                    text += doc[page_num].get_text()
                doc.close()
                return text

            paper_text = await loop.run_in_executor(_executor, extract_text)

        if not paper_text:
            return {"status": "error", "error": "No paper text provided"}

        # Use Gemini to analyze the text
        loop = asyncio.get_event_loop()

        def analyze():
            try:
                client = self._get_genai_client()
                from google.genai import types

                prompt = """Analyze this silicon photonics paper text and extract fabrication process information.

Return a JSON object with:
- waveguide_thickness_nm: Waveguide thickness in nanometers (e.g., 220)
- material: Primary waveguide material (e.g., "Si", "SiN", "Si3N4")
- cladding: Cladding material (e.g., "SiO2", "air")
- wavelength_nm: Operating wavelength in nm (e.g., 1550)
- foundry_hint: Any foundry/fab mentioned (e.g., "AIM", "AMF", "IMEC")
- confidence: Your confidence level ("high", "medium", "low")
- notes: Any relevant notes about the process

Paper text:
""" + paper_text[:10000]  # Limit text length

                response = client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=[types.Part.from_text(text=prompt)]
                )

                response_text = response.text.strip()

                # Parse JSON from response
                if "```" in response_text:
                    response_text = response_text.split("```")[1]
                    if response_text.startswith("json"):
                        response_text = response_text[4:]
                    response_text = response_text.strip()

                return json.loads(response_text)

            except Exception as e:
                # Fallback: keyword-based extraction
                process_info = {
                    "waveguide_thickness_nm": None,
                    "material": None,
                    "wavelength_nm": None,
                    "foundry_hint": None,
                    "confidence": "low",
                    "notes": f"Extraction failed: {e}"
                }

                # Simple keyword matching
                text_lower = paper_text.lower()

                if "220 nm" in text_lower or "220nm" in text_lower:
                    process_info["waveguide_thickness_nm"] = 220
                if "silicon nitride" in text_lower or "sin" in text_lower:
                    process_info["material"] = "SiN"
                elif "silicon" in text_lower:
                    process_info["material"] = "Si"
                if "1550" in paper_text:
                    process_info["wavelength_nm"] = 1550
                elif "1310" in paper_text:
                    process_info["wavelength_nm"] = 1310

                return process_info

        process_info = await loop.run_in_executor(_executor, analyze)

        return {
            "status": "success",
            "process_info": process_info
        }

    @tool_handler
    async def _list_available_pdks(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """List all available PDKs."""
        return {
            "status": "success",
            "pdks": AVAILABLE_PDKS,
            "count": len(AVAILABLE_PDKS)
        }

    @tool_handler
    async def _match_pdk(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Match process info to compatible PDKs."""
        process_info = args["process_info"]

        matches = []

        for pdk_id, pdk in AVAILABLE_PDKS.items():
            score = 0
            notes = []

            # Check thickness match
            if process_info.get("waveguide_thickness_nm"):
                if abs(pdk["process"]["waveguide_thickness_nm"] - process_info["waveguide_thickness_nm"]) < 10:
                    score += 30
                    notes.append("Thickness matches")
                else:
                    notes.append("Thickness mismatch")

            # Check material match
            if process_info.get("material"):
                pdk_material = "Si" if "si" in pdk_id.lower() and "sin" not in pdk_id.lower() else "SiN"
                if process_info["material"].lower() in pdk_material.lower():
                    score += 25
                    notes.append("Material matches")

            # Check wavelength match
            if process_info.get("wavelength_nm"):
                if abs(pdk["wavelength_nm"] - process_info["wavelength_nm"]) < 50:
                    score += 20
                    notes.append("Wavelength matches")

            # Check foundry hint
            if process_info.get("foundry_hint"):
                if process_info["foundry_hint"].lower() in pdk_id.lower():
                    score += 25
                    notes.append("Foundry matches")

            if score > 0:
                matches.append({
                    "pdk_id": pdk_id,
                    "pdk_name": pdk["name"],
                    "confidence": score,
                    "notes": notes
                })

        # Sort by confidence
        matches.sort(key=lambda x: x["confidence"], reverse=True)

        return {
            "status": "success",
            "matches": matches,
            "best_match": matches[0] if matches else None
        }

    @tool_handler
    async def _get_pdk_layer_mapping(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get layer mapping for a PDK."""
        pdk_name = args["pdk_name"]
        source_layers = args.get("source_layers", [(1, 0)])

        if pdk_name not in AVAILABLE_PDKS:
            return {"status": "error", "error": f"Unknown PDK: {pdk_name}"}

        pdk = AVAILABLE_PDKS[pdk_name]
        pdk_layers = pdk["layers"]

        # Create mapping - map source layer (1,0) to waveguide layer
        mapping = {}
        for source in source_layers:
            source_key = f"{source[0]}_{source[1]}"
            if source[0] == 1 and source[1] == 0:
                # Main device layer -> waveguide
                wg_layer = pdk_layers.get("waveguide", pdk_layers.get("WGCORE", pdk_layers.get("Si_Full", (1, 0))))
                mapping[source_key] = list(wg_layer)
            else:
                # Keep other layers as-is for now
                mapping[source_key] = list(source)

        return {
            "status": "success",
            "pdk_name": pdk_name,
            "mapping": mapping,
            "pdk_layers": pdk_layers
        }

    @tool_handler
    async def _convert_to_pdk(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Convert GDS to PDK layers."""
        gds_path = Path(args["gds_path"])
        pdk_name = args["pdk_name"]
        output_path = Path(args["output_path"])
        custom_mapping = args.get("layer_mapping")

        if not gds_path.exists():
            return {"status": "error", "error": f"GDS not found: {gds_path}"}

        if pdk_name not in AVAILABLE_PDKS:
            return {"status": "error", "error": f"Unknown PDK: {pdk_name}"}

        loop = asyncio.get_event_loop()

        def convert():
            import gdstk

            # Read GDS
            lib = gdstk.read_gds(str(gds_path))

            # Get or create layer mapping
            pdk = AVAILABLE_PDKS[pdk_name]
            wg_layer = pdk["layers"].get("waveguide", pdk["layers"].get("WGCORE", (1, 0)))

            # Create new library with remapped layers
            new_lib = gdstk.Library()

            for cell in lib.cells:
                new_cell = gdstk.Cell(cell.name)

                for polygon in cell.polygons:
                    # Remap layer (1, 0) to PDK waveguide layer
                    if polygon.layer == 1 and polygon.datatype == 0:
                        new_polygon = polygon.copy()
                        new_polygon.layer = wg_layer[0]
                        new_polygon.datatype = wg_layer[1]
                        new_cell.add(new_polygon)
                    else:
                        new_cell.add(polygon.copy())

                new_lib.add(new_cell)

            # Write output
            output_path.parent.mkdir(parents=True, exist_ok=True)
            new_lib.write_gds(str(output_path))

            return {"success": True}

        try:
            result = await loop.run_in_executor(_executor, convert)

            return {
                "status": "success",
                "output_path": str(output_path),
                "pdk_name": pdk_name
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    @tool_handler
    async def _run_drc(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Run design rule check."""
        gds_path = Path(args["gds_path"])
        pdk_name = args["pdk_name"]

        if not gds_path.exists():
            return {"status": "error", "error": f"GDS not found: {gds_path}"}

        if pdk_name not in AVAILABLE_PDKS:
            return {"status": "error", "error": f"Unknown PDK: {pdk_name}"}

        pdk = AVAILABLE_PDKS[pdk_name]
        rules = pdk["design_rules"]

        loop = asyncio.get_event_loop()

        def check_rules():
            import gdstk
            import numpy as np

            violations = []

            lib = gdstk.read_gds(str(gds_path))

            for cell in lib.cells:
                for polygon in cell.polygons:
                    # Get bounding box
                    bbox = polygon.bounding_box()
                    if bbox is None:
                        continue

                    width = bbox[1][0] - bbox[0][0]
                    height = bbox[1][1] - bbox[0][1]

                    # Check minimum width
                    min_dim = min(width, height)
                    if min_dim < rules["min_waveguide_width_um"]:
                        violations.append({
                            "rule": "min_waveguide_width",
                            "expected": rules["min_waveguide_width_um"],
                            "actual": min_dim,
                            "location": {"x": bbox[0][0], "y": bbox[0][1]},
                            "severity": "error"
                        })

            return violations

        violations = await loop.run_in_executor(_executor, check_rules)

        return {
            "status": "success",
            "pdk_name": pdk_name,
            "violations": violations,
            "passed": len(violations) == 0,
            "violation_count": len(violations)
        }

    @tool_handler
    async def _suggest_drc_fixes(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Suggest fixes for DRC violations."""
        violations = args["violations"]

        fixes = []
        for violation in violations:
            rule = violation.get("rule", "")
            expected = violation.get("expected")
            actual = violation.get("actual")

            if rule == "min_waveguide_width":
                fixes.append({
                    "violation": violation,
                    "suggestion": f"Increase waveguide width from {actual:.3f} to at least {expected:.3f} um",
                    "action": "modify_parameter",
                    "parameter": "width",
                    "new_value": expected * 1.1  # 10% margin
                })
            elif rule == "min_gap":
                fixes.append({
                    "violation": violation,
                    "suggestion": f"Increase gap from {actual:.3f} to at least {expected:.3f} um",
                    "action": "modify_parameter",
                    "parameter": "gap",
                    "new_value": expected * 1.1
                })
            elif rule == "min_bend_radius":
                fixes.append({
                    "violation": violation,
                    "suggestion": f"Increase bend radius from {actual:.3f} to at least {expected:.3f} um",
                    "action": "modify_parameter",
                    "parameter": "radius",
                    "new_value": expected * 1.1
                })
            else:
                fixes.append({
                    "violation": violation,
                    "suggestion": "Manual review required",
                    "action": "manual"
                })

        return {
            "status": "success",
            "fixes": fixes,
            "auto_fixable": sum(1 for f in fixes if f["action"] != "manual"),
            "manual_required": sum(1 for f in fixes if f["action"] == "manual")
        }

    # =========================================================================
    # New PDK Document Parsing Tools
    # =========================================================================

    # Cache for loaded PDKs
    _loaded_pdks: Dict[str, Any] = {}

    @tool_handler
    async def _parse_pdk_document(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Parse a PDK PDF document into structured definition."""
        if not PDK_MODULE_AVAILABLE:
            return {"status": "error", "error": "PDK module not available"}

        pdf_path = Path(args["pdf_path"])
        pdk_name = args.get("pdk_name")
        save_path = args.get("save_path")

        if not pdf_path.exists():
            return {"status": "error", "error": f"PDF not found: {pdf_path}"}

        try:
            parser = PDKParser()
            pdk = await parser.parse_pdf(str(pdf_path), pdk_name)

            # Cache the parsed PDK
            cache_name = pdk_name or pdk.name.lower().replace(" ", "_")
            self._loaded_pdks[cache_name] = pdk

            # Save if requested
            if save_path:
                pdk.save(save_path)

            return {
                "status": "success",
                "pdk_name": pdk.name,
                "cache_key": cache_name,
                "parsing_confidence": pdk.parsing_confidence,
                "summary": {
                    "layers": len(pdk.layers),
                    "materials": len(pdk.materials),
                    "cross_sections": len(pdk.cross_sections),
                    "design_rules": len(pdk.design_rules),
                },
                "layer_names": list(pdk.layers.keys()),
                "material_names": list(pdk.materials.keys()),
            }
        except Exception as e:
            logger.exception("Failed to parse PDK document")
            return {"status": "error", "error": str(e)}

    @tool_handler
    async def _load_builtin_pdk(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Load a pre-defined builtin PDK."""
        if not PDK_MODULE_AVAILABLE:
            return {"status": "error", "error": "PDK module not available"}

        pdk_name = args["pdk_name"]

        try:
            pdk = load_builtin_pdk(pdk_name)

            # Cache it
            self._loaded_pdks[pdk_name] = pdk

            return {
                "status": "success",
                "pdk_name": pdk.name,
                "cache_key": pdk_name,
                "foundry": pdk.foundry,
                "description": pdk.description,
                "summary": {
                    "layers": len(pdk.layers),
                    "materials": len(pdk.materials),
                    "cross_sections": len(pdk.cross_sections),
                    "design_rules": len(pdk.design_rules),
                    "box_thickness_um": pdk.box_thickness_um,
                },
                "layer_names": list(pdk.layers.keys()),
            }
        except FileNotFoundError:
            available = list_builtin_pdks()
            return {
                "status": "error",
                "error": f"Builtin PDK not found: {pdk_name}",
                "available_pdks": list(available.keys()),
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    @tool_handler
    async def _list_pdk_layers_full(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """List all layers in a PDK with complete properties."""
        if not PDK_MODULE_AVAILABLE:
            return {"status": "error", "error": "PDK module not available"}

        pdk_name = args["pdk_name"]

        # Try to get from cache
        pdk = self._loaded_pdks.get(pdk_name)
        if not pdk:
            # Try to load builtin
            try:
                pdk = load_builtin_pdk(pdk_name)
                self._loaded_pdks[pdk_name] = pdk
            except FileNotFoundError:
                return {
                    "status": "error",
                    "error": f"PDK not loaded: {pdk_name}. Use load_builtin_pdk or parse_pdk_document first."
                }

        layers_info = []
        for layer_name, layer in pdk.layers.items():
            info = {
                "name": layer.name,
                "gds_number": layer.gds_number,
                "datatype": layer.datatype,
                "purpose": layer.purpose,
                "description": layer.description,
                "color": layer.color,
            }

            # Add geometry info if available
            if layer.thickness_nm:
                info["thickness_nm"] = layer.thickness_nm
            if layer.etch_depth_nm:
                info["etch_depth_nm"] = layer.etch_depth_nm
            if layer.sidewall_angle_deg:
                info["sidewall_angle_deg"] = layer.sidewall_angle_deg
            if layer.min_width_nm:
                info["min_width_nm"] = layer.min_width_nm
            if layer.min_spacing_nm:
                info["min_spacing_nm"] = layer.min_spacing_nm

            # Add material info if available
            if layer.material_name:
                info["material_name"] = layer.material_name
                material = pdk.get_material(layer.material_name)
                if material:
                    info["material"] = {
                        "n_ordinary": material.n_ordinary,
                        "is_anisotropic": material.is_anisotropic,
                    }
                    if material.is_anisotropic:
                        info["material"]["n_extraordinary"] = material.n_extraordinary
                        info["material"]["crystal_cut"] = material.crystal_cut

            layers_info.append(info)

        return {
            "status": "success",
            "pdk_name": pdk.name,
            "layer_count": len(layers_info),
            "layers": layers_info,
        }

    @tool_handler
    async def _get_layer_material_properties(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get Tidy3D-compatible material properties for a PDK layer."""
        if not PDK_MODULE_AVAILABLE:
            return {"status": "error", "error": "PDK module not available"}

        pdk_name = args["pdk_name"]
        layer_name = args["layer_name"]

        # Get PDK
        pdk = self._loaded_pdks.get(pdk_name)
        if not pdk:
            try:
                pdk = load_builtin_pdk(pdk_name)
                self._loaded_pdks[pdk_name] = pdk
            except FileNotFoundError:
                return {"status": "error", "error": f"PDK not loaded: {pdk_name}"}

        layer = pdk.get_layer(layer_name)
        if not layer:
            return {
                "status": "error",
                "error": f"Layer not found: {layer_name}",
                "available_layers": list(pdk.layers.keys()),
            }

        if not layer.material_name:
            return {"status": "error", "error": f"Layer {layer_name} has no material assigned"}

        material = pdk.get_material(layer.material_name)
        if not material:
            return {"status": "error", "error": f"Material not found: {layer.material_name}"}

        # Build Tidy3D-compatible response
        result = {
            "status": "success",
            "layer_name": layer_name,
            "material_name": material.name,
            "is_anisotropic": material.is_anisotropic,
            "wavelength_nm": material.wavelength_nm,
            "tidy3d_params": {},
        }

        if material.is_anisotropic:
            result["n_ordinary"] = material.n_ordinary
            result["n_extraordinary"] = material.n_extraordinary
            result["crystal_cut"] = material.crystal_cut
            result["tidy3d_params"] = {
                "type": "AnisotropicMedium",
                "permittivity_xx": material.n_ordinary ** 2,
                "permittivity_yy": material.n_extraordinary ** 2,
                "permittivity_zz": material.n_ordinary ** 2,
            }
        else:
            result["n"] = material.n_ordinary
            result["tidy3d_params"] = {
                "type": "Medium",
                "permittivity": material.n_ordinary ** 2,
            }

        # Add cladding info
        if material.clad_n:
            result["cladding_n"] = material.clad_n
            result["cladding_permittivity"] = material.clad_n ** 2

        # Add geometry info from layer
        if layer.thickness_nm:
            result["thickness_nm"] = layer.thickness_nm
            result["thickness_um"] = layer.thickness_nm / 1000
        if layer.etch_depth_nm:
            result["etch_depth_nm"] = layer.etch_depth_nm
        if layer.sidewall_angle_deg:
            result["sidewall_angle_deg"] = layer.sidewall_angle_deg

        return result

    @tool_handler
    async def _get_pdk_cross_sections(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get waveguide cross-section definitions from a PDK."""
        if not PDK_MODULE_AVAILABLE:
            return {"status": "error", "error": "PDK module not available"}

        pdk_name = args["pdk_name"]

        # Get PDK
        pdk = self._loaded_pdks.get(pdk_name)
        if not pdk:
            try:
                pdk = load_builtin_pdk(pdk_name)
                self._loaded_pdks[pdk_name] = pdk
            except FileNotFoundError:
                return {"status": "error", "error": f"PDK not loaded: {pdk_name}"}

        cross_sections = []
        for xs_name, xs in pdk.cross_sections.items():
            cross_sections.append({
                "name": xs.name,
                "film_thickness_nm": xs.film_thickness_nm,
                "etch_depth_nm": xs.etch_depth_nm,
                "slab_thickness_nm": xs.slab_thickness_nm,
                "sidewall_angle_deg": xs.sidewall_angle_deg,
                "material_name": xs.material_name,
                "cladding_material": xs.cladding_material,
                "description": xs.description,
                "is_fully_etched": xs.is_fully_etched,
                "is_rib": xs.is_rib,
            })

        return {
            "status": "success",
            "pdk_name": pdk.name,
            "cross_section_count": len(cross_sections),
            "cross_sections": cross_sections,
        }


# Entry point
async def main():
    logging.basicConfig(level=logging.INFO)
    server = PDKServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
