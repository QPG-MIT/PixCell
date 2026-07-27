"""
PDK (Process Design Kit) Module

Provides data models, parsing, and conversion utilities for foundry PDKs.
Enables "Design Once, Simulate on Any Foundry" workflow.

Usage:
    from gg.pdk import PDKDefinition, PDKParser, PDKTidy3DConverter
    from gg.pdk.builtin import load_builtin_pdk

    # Load builtin PDK
    pdk = load_builtin_pdk("generic_si220")

    # Or parse from PDF
    parser = PDKParser()
    pdk = await parser.parse_pdf("foundry_pdk.pdf")

    # Use with Tidy3D
    converter = PDKTidy3DConverter(pdk)
    medium = converter.get_medium_for_layer("TFLN_WG1")
"""

from .schema import (
    PDKLayer,
    PDKMaterial,
    PDKCrossSection,
    PDKDesignRule,
    PDKDefinition,
    LayerPurpose,
)

from .parser import (
    PDKParser,
    parse_pdk_document,
    parse_pdk_document_sync,
)

from .tidy3d_converter import (
    PDKTidy3DConverter,
    is_tidy3d_available,
    create_medium_from_pdk_material,
    get_material_preset_from_pdk,
    get_linbo3_from_library,
)

from .builtin import (
    load_builtin_pdk,
    list_builtin_pdks,
    GENERIC_SI220,
)

__all__ = [
    # Schema
    "PDKLayer",
    "PDKMaterial",
    "PDKCrossSection",
    "PDKDesignRule",
    "PDKDefinition",
    "LayerPurpose",
    # Parser
    "PDKParser",
    "parse_pdk_document",
    "parse_pdk_document_sync",
    # Tidy3D Converter
    "PDKTidy3DConverter",
    "is_tidy3d_available",
    "create_medium_from_pdk_material",
    "get_material_preset_from_pdk",
    "get_linbo3_from_library",
    # Builtin PDKs
    "load_builtin_pdk",
    "list_builtin_pdks",
    "GENERIC_SI220",
]
