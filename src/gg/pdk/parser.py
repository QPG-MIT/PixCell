"""
PDK PDF Parser

AI-powered extraction of PDK definitions from foundry PDF documents.
Uses Gemini to parse layer tables, material properties, and design rules.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .schema import (
    PDKDefinition,
    PDKLayer,
    PDKMaterial,
    PDKCrossSection,
    PDKDesignRule,
    LayerPurpose,
    get_layer_color,
)

logger = logging.getLogger(__name__)

# Thread pool for blocking operations
_executor = ThreadPoolExecutor(max_workers=2)


# =============================================================================
# Extraction Prompts
# =============================================================================

LAYER_EXTRACTION_PROMPT = """Analyze this PDK (Process Design Kit) document and extract all layer definitions.

For each layer, extract:
- name: Layer name (e.g., "TFLN_WG1", "WGCORE", "MET1")
- gds_number: GDS layer number (0-255)
- datatype: GDS datatype (default 0 if not specified)
- purpose: One of: "core", "slab", "metal", "via", "heater", "pad", "marker", "cladding", "trench"
- description: What the layer is for
- thickness_nm: Film thickness in nanometers (if specified)
- etch_depth_nm: Etch depth in nanometers (if specified)
- sidewall_angle_deg: Sidewall angle in degrees (if specified)
- material_name: Associated material (e.g., "LN", "Si", "Cu")
- min_width_nm: Minimum feature width (if specified)
- min_spacing_nm: Minimum spacing (if specified)

Return a JSON array of layer objects. Example:
```json
[
  {
    "name": "TFLN_WG1",
    "gds_number": 10,
    "datatype": 0,
    "purpose": "core",
    "description": "First TFLN etch layer: 400nm etch depth",
    "thickness_nm": 600,
    "etch_depth_nm": 400,
    "sidewall_angle_deg": 55,
    "material_name": "LN",
    "min_width_nm": 100,
    "min_spacing_nm": 400
  }
]
```

PDK Document Text:
"""

MATERIAL_EXTRACTION_PROMPT = """Analyze this PDK document and extract all material properties.

For each material, extract:
- name: Material identifier (e.g., "LN_Xcut", "Si", "SiN")
- n_ordinary: Ordinary refractive index
- n_extraordinary: Extraordinary refractive index (for anisotropic materials like LN)
- is_anisotropic: true/false
- crystal_cut: Crystal orientation if specified (e.g., "X-cut", "Z-cut")
- wavelength_nm: Reference wavelength for indices
- clad_n: Cladding refractive index
- description: Description of the material

Look for:
- Refractive indices (n, n_o, n_e, ordinary, extraordinary)
- Wavelength specifications (1550nm, 1310nm, C-band, O-band)
- Crystal cuts for LN (X-cut, Z-cut)
- Material types (LiNbO3, Silicon, SiN, SiO2, Cu, Al)

Return a JSON array of material objects. Example:
```json
[
  {
    "name": "LN_Xcut",
    "n_ordinary": 2.211,
    "n_extraordinary": 2.138,
    "is_anisotropic": true,
    "crystal_cut": "X-cut",
    "wavelength_nm": 1550,
    "clad_n": 1.44,
    "description": "X-cut Lithium Niobate"
  }
]
```

PDK Document Text:
"""

CROSS_SECTION_PROMPT = """Analyze this PDK document and extract waveguide cross-section definitions.

For each cross-section, extract:
- name: Cross-section identifier (e.g., "WG1", "ridge", "strip")
- film_thickness_nm: Total film thickness before etching
- etch_depth_nm: Etch depth
- slab_thickness_nm: Remaining slab thickness (film - etch, or 0 for full etch)
- sidewall_angle_deg: Sidewall angle in degrees
- material_name: Core material name
- cladding_material: Cladding material (typically "SiO2")
- description: Description of the cross-section

Look for:
- Waveguide types (rib, ridge, strip, fully etched)
- Etch depths and film thicknesses
- Sidewall angles (fabrication angle vs sidewall angle)

Return a JSON array. Example:
```json
[
  {
    "name": "WG1_rib",
    "film_thickness_nm": 600,
    "etch_depth_nm": 400,
    "slab_thickness_nm": 200,
    "sidewall_angle_deg": 55,
    "material_name": "LN",
    "cladding_material": "SiO2",
    "description": "Primary waveguide: 400nm etch in 600nm TFLN"
  }
]
```

PDK Document Text:
"""

DESIGN_RULES_PROMPT = """Analyze this PDK document and extract design rules.

For each rule, extract:
- rule_name: Rule identifier (e.g., "min_width", "min_spacing", "min_bend_radius")
- layer_name: Layer this rule applies to (null for global rules)
- min_value_um: Minimum value in micrometers
- max_value_um: Maximum value in micrometers (if applicable)
- description: Description of the rule

Look for:
- Minimum widths and spacings
- Minimum bend radii
- Overlay/alignment tolerances
- Enclosure rules
- Layer interaction rules

Return a JSON array. Example:
```json
[
  {
    "rule_name": "min_width",
    "layer_name": "TFLN_WG1",
    "min_value_um": 0.1,
    "description": "Minimum waveguide width"
  }
]
```

PDK Document Text:
"""

METADATA_PROMPT = """Analyze this PDK document and extract general metadata.

Extract:
- name: PDK name (e.g., "Generic Si 220nm")
- version: Version string if available
- foundry: Foundry/company name
- description: Brief description of the platform
- substrate_material: Substrate material (typically "Si")
- box_thickness_um: Buried oxide thickness in micrometers

Return a JSON object. Example:
```json
{
  "name": "Example TFLN Platform",
  "version": "1.0",
  "foundry": "ExampleFoundry",
  "description": "600nm X-cut TFLN platform",
  "substrate_material": "Si",
  "box_thickness_um": 8.2
}
```

PDK Document Text:
"""


# =============================================================================
# PDF Text Extraction
# =============================================================================

def extract_text_from_pdf(pdf_path: str, max_pages: int = 30) -> str:
    """
    Extract text from a PDF file.

    Args:
        pdf_path: Path to PDF file
        max_pages: Maximum number of pages to process

    Returns:
        Extracted text content
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        raise ImportError("PyMuPDF is required. Install with: pip install pymupdf")

    doc = fitz.open(pdf_path)
    text_parts = []

    for page_num in range(min(max_pages, len(doc))):
        page = doc[page_num]
        text_parts.append(f"\n--- Page {page_num + 1} ---\n")
        text_parts.append(page.get_text())

    doc.close()
    return "".join(text_parts)


def extract_tables_from_pdf(pdf_path: str) -> List[List[List[str]]]:
    """
    Extract tables from PDF (best effort).

    Args:
        pdf_path: Path to PDF file

    Returns:
        List of tables, each table is a list of rows
    """
    try:
        import fitz
    except ImportError:
        return []

    tables = []
    doc = fitz.open(pdf_path)

    for page in doc:
        # Try to find table-like structures
        blocks = page.get_text("dict")["blocks"]
        for block in blocks:
            if block.get("type") == 0:  # Text block
                lines = block.get("lines", [])
                if len(lines) > 2:
                    # Might be a table
                    table_rows = []
                    for line in lines:
                        row = [span.get("text", "") for span in line.get("spans", [])]
                        if row:
                            table_rows.append(row)
                    if len(table_rows) > 2:
                        tables.append(table_rows)

    doc.close()
    return tables


# =============================================================================
# AI-Powered Parsing
# =============================================================================

class PDKParser:
    """
    AI-powered parser for PDK PDF documents.

    Uses Gemini to extract structured information from PDK documents.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize parser.

        Args:
            api_key: Gemini API key (uses GEMINI_API_KEY env var if not provided)
        """
        self._api_key = api_key or os.getenv("GEMINI_API_KEY")
        self._client = None

    def _get_client(self):
        """Get or create Gemini client."""
        if self._client is None:
            if not self._api_key:
                raise ValueError(
                    "GEMINI_API_KEY not set. Provide api_key or set environment variable."
                )
            from google import genai
            self._client = genai.Client(api_key=self._api_key)
        return self._client

    def _call_ai(self, prompt: str, text: str) -> str:
        """
        Call Gemini API with prompt and text.

        Args:
            prompt: Extraction prompt
            text: PDK document text

        Returns:
            AI response text
        """
        client = self._get_client()
        from google.genai import types

        full_prompt = prompt + text[:50000]  # Limit text length

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[types.Part.from_text(text=full_prompt)],
            config=types.GenerateContentConfig(
                temperature=0.1,  # Low temperature for structured output
            ),
        )

        return response.text.strip()

    def _parse_json_response(self, response: str) -> Any:
        """Parse JSON from AI response, handling markdown code blocks."""
        # Remove markdown code blocks if present
        if "```" in response:
            # Find JSON content between code blocks
            match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", response)
            if match:
                response = match.group(1)

        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON response: {e}")
            return None

    async def parse_pdf(
        self,
        pdf_path: str,
        pdk_name: Optional[str] = None,
    ) -> PDKDefinition:
        """
        Parse a PDK PDF and extract complete definition.

        Args:
            pdf_path: Path to PDF file
            pdk_name: Optional override for PDK name

        Returns:
            PDKDefinition with extracted information
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        loop = asyncio.get_event_loop()

        # Extract text (blocking)
        def extract():
            return extract_text_from_pdf(str(pdf_path))

        text = await loop.run_in_executor(_executor, extract)

        # Extract all components in parallel
        def extract_metadata():
            response = self._call_ai(METADATA_PROMPT, text)
            return self._parse_json_response(response)

        def extract_layers():
            response = self._call_ai(LAYER_EXTRACTION_PROMPT, text)
            return self._parse_json_response(response)

        def extract_materials():
            response = self._call_ai(MATERIAL_EXTRACTION_PROMPT, text)
            return self._parse_json_response(response)

        def extract_cross_sections():
            response = self._call_ai(CROSS_SECTION_PROMPT, text)
            return self._parse_json_response(response)

        def extract_design_rules():
            response = self._call_ai(DESIGN_RULES_PROMPT, text)
            return self._parse_json_response(response)

        # Run extractions in thread pool
        metadata_future = loop.run_in_executor(_executor, extract_metadata)
        layers_future = loop.run_in_executor(_executor, extract_layers)
        materials_future = loop.run_in_executor(_executor, extract_materials)
        cross_sections_future = loop.run_in_executor(_executor, extract_cross_sections)
        design_rules_future = loop.run_in_executor(_executor, extract_design_rules)

        # Gather results
        metadata = await metadata_future
        layers_data = await layers_future
        materials_data = await materials_future
        cross_sections_data = await cross_sections_future
        design_rules_data = await design_rules_future

        # Build PDKDefinition
        return self._build_pdk_definition(
            metadata=metadata or {},
            layers_data=layers_data or [],
            materials_data=materials_data or [],
            cross_sections_data=cross_sections_data or [],
            design_rules_data=design_rules_data or [],
            source_pdf=str(pdf_path),
            name_override=pdk_name,
        )

    def parse_pdf_sync(
        self,
        pdf_path: str,
        pdk_name: Optional[str] = None,
    ) -> PDKDefinition:
        """
        Synchronous version of parse_pdf.

        Args:
            pdf_path: Path to PDF file
            pdk_name: Optional override for PDK name

        Returns:
            PDKDefinition with extracted information
        """
        return asyncio.run(self.parse_pdf(pdf_path, pdk_name))

    def _build_pdk_definition(
        self,
        metadata: Dict[str, Any],
        layers_data: List[Dict[str, Any]],
        materials_data: List[Dict[str, Any]],
        cross_sections_data: List[Dict[str, Any]],
        design_rules_data: List[Dict[str, Any]],
        source_pdf: str,
        name_override: Optional[str] = None,
    ) -> PDKDefinition:
        """Build PDKDefinition from extracted data."""

        # Build layers
        layers = {}
        for i, layer_dict in enumerate(layers_data):
            try:
                name = layer_dict.get("name", f"Layer_{i}")
                purpose = layer_dict.get("purpose", "core")

                layer = PDKLayer(
                    name=name,
                    gds_number=int(layer_dict.get("gds_number", i + 1)),
                    datatype=int(layer_dict.get("datatype", 0)),
                    purpose=purpose,
                    description=layer_dict.get("description", ""),
                    thickness_nm=layer_dict.get("thickness_nm"),
                    etch_depth_nm=layer_dict.get("etch_depth_nm"),
                    sidewall_angle_deg=layer_dict.get("sidewall_angle_deg"),
                    material_name=layer_dict.get("material_name"),
                    min_width_nm=layer_dict.get("min_width_nm"),
                    min_spacing_nm=layer_dict.get("min_spacing_nm"),
                    color=get_layer_color(purpose, i),
                )
                layers[name] = layer
            except (KeyError, ValueError, TypeError) as e:
                logger.warning(f"Failed to parse layer {i}: {e}")

        # Build materials
        materials = {}
        for i, mat_dict in enumerate(materials_data):
            try:
                name = mat_dict.get("name", f"Material_{i}")
                material = PDKMaterial(
                    name=name,
                    n_ordinary=float(mat_dict.get("n_ordinary", 1.5)),
                    n_extraordinary=mat_dict.get("n_extraordinary"),
                    is_anisotropic=mat_dict.get("is_anisotropic", False),
                    crystal_cut=mat_dict.get("crystal_cut"),
                    wavelength_nm=float(mat_dict.get("wavelength_nm", 1550)),
                    clad_n=float(mat_dict.get("clad_n", 1.44)),
                    description=mat_dict.get("description", ""),
                )
                materials[name] = material
            except (KeyError, ValueError, TypeError) as e:
                logger.warning(f"Failed to parse material {i}: {e}")

        # Build cross-sections
        cross_sections = {}
        for i, xs_dict in enumerate(cross_sections_data):
            try:
                name = xs_dict.get("name", f"XS_{i}")
                xs = PDKCrossSection(
                    name=name,
                    film_thickness_nm=float(xs_dict.get("film_thickness_nm", 220)),
                    etch_depth_nm=float(xs_dict.get("etch_depth_nm", 220)),
                    slab_thickness_nm=float(xs_dict.get("slab_thickness_nm", 0)),
                    sidewall_angle_deg=float(xs_dict.get("sidewall_angle_deg", 90)),
                    material_name=xs_dict.get("material_name", "Si"),
                    cladding_material=xs_dict.get("cladding_material", "SiO2"),
                    description=xs_dict.get("description", ""),
                )
                cross_sections[name] = xs
            except (KeyError, ValueError, TypeError) as e:
                logger.warning(f"Failed to parse cross-section {i}: {e}")

        # Build design rules
        design_rules = []
        for i, rule_dict in enumerate(design_rules_data):
            try:
                rule = PDKDesignRule(
                    rule_name=rule_dict.get("rule_name", f"rule_{i}"),
                    layer_name=rule_dict.get("layer_name"),
                    min_value_um=rule_dict.get("min_value_um"),
                    max_value_um=rule_dict.get("max_value_um"),
                    description=rule_dict.get("description", ""),
                )
                design_rules.append(rule)
            except (KeyError, ValueError, TypeError) as e:
                logger.warning(f"Failed to parse design rule {i}: {e}")

        # Calculate parsing confidence
        confidence = 0.0
        if layers:
            confidence += 0.3
        if materials:
            confidence += 0.3
        if cross_sections:
            confidence += 0.2
        if design_rules:
            confidence += 0.2

        return PDKDefinition(
            name=name_override or metadata.get("name", "Unknown PDK"),
            version=metadata.get("version", "1.0"),
            foundry=metadata.get("foundry", ""),
            description=metadata.get("description", ""),
            layers=layers,
            materials=materials,
            cross_sections=cross_sections,
            design_rules=design_rules,
            substrate_material=metadata.get("substrate_material", "Si"),
            box_thickness_um=float(metadata.get("box_thickness_um", 2.0)),
            source_pdf=source_pdf,
            parsing_confidence=confidence,
        )


# =============================================================================
# Convenience Functions
# =============================================================================

async def parse_pdk_document(
    pdf_path: str,
    pdk_name: Optional[str] = None,
    api_key: Optional[str] = None,
) -> PDKDefinition:
    """
    Parse a PDK PDF document.

    Args:
        pdf_path: Path to PDF file
        pdk_name: Optional override for PDK name
        api_key: Optional Gemini API key

    Returns:
        PDKDefinition with extracted information
    """
    parser = PDKParser(api_key=api_key)
    return await parser.parse_pdf(pdf_path, pdk_name)


def parse_pdk_document_sync(
    pdf_path: str,
    pdk_name: Optional[str] = None,
    api_key: Optional[str] = None,
) -> PDKDefinition:
    """
    Synchronous version of parse_pdk_document.

    Args:
        pdf_path: Path to PDF file
        pdk_name: Optional override for PDK name
        api_key: Optional Gemini API key

    Returns:
        PDKDefinition with extracted information
    """
    parser = PDKParser(api_key=api_key)
    return parser.parse_pdf_sync(pdf_path, pdk_name)
