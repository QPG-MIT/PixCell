"""
PDK Schema - Data models for foundry Process Design Kits

Defines structured representations for:
- Layers (GDS layer definitions with material associations)
- Materials (optical properties including anisotropic materials)
- Cross-sections (waveguide geometries with etch depths)
- Design rules (minimum width, spacing, etc.)
- Complete PDK definitions
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional
from pathlib import Path


# =============================================================================
# Layer Purpose Constants
# =============================================================================

class LayerPurpose:
    """Standard layer purposes for categorization."""
    CORE = "core"           # Waveguide core layers
    SLAB = "slab"           # Partial etch / slab layers
    METAL = "metal"         # Metallization layers
    VIA = "via"             # Via / interconnect layers
    MARKER = "marker"       # Alignment / marker layers
    HEATER = "heater"       # Heater layers
    DOPING = "doping"       # Doping regions
    TRENCH = "trench"       # Deep trench / release layers
    PAD = "pad"             # Bond pad layers
    CLADDING = "cladding"   # Cladding opening layers


# =============================================================================
# PDK Layer
# =============================================================================

@dataclass
class PDKLayer:
    """
    Individual layer definition from a PDK.

    Attributes:
        name: Layer name (e.g., "TFLN_WG1", "WGCORE")
        gds_number: GDS layer number (0-255)
        datatype: GDS datatype (default 0)
        purpose: Layer purpose category (core, slab, metal, etc.)
        description: Human-readable description
        thickness_nm: Film thickness in nanometers
        etch_depth_nm: Etch depth in nanometers (for waveguide layers)
        sidewall_angle_deg: Sidewall angle in degrees (e.g., 55 for TFLN)
        material_name: Reference to PDKMaterial name
        min_width_nm: Minimum feature width
        min_spacing_nm: Minimum spacing between features
        color: Hex color for visualization (e.g., "#2E86AB")
    """
    name: str
    gds_number: int
    datatype: int = 0
    purpose: str = LayerPurpose.CORE
    description: str = ""

    # Physical properties
    thickness_nm: Optional[float] = None
    etch_depth_nm: Optional[float] = None
    sidewall_angle_deg: Optional[float] = None

    # Material reference
    material_name: Optional[str] = None

    # Design rules
    min_width_nm: Optional[float] = None
    min_spacing_nm: Optional[float] = None

    # Visual properties
    color: str = "#808080"

    @property
    def gds_tuple(self) -> tuple:
        """Return (layer, datatype) tuple for GDS operations."""
        return (self.gds_number, self.datatype)

    @property
    def thickness_um(self) -> Optional[float]:
        """Return thickness in micrometers."""
        return self.thickness_nm / 1000 if self.thickness_nm else None

    @property
    def etch_depth_um(self) -> Optional[float]:
        """Return etch depth in micrometers."""
        return self.etch_depth_nm / 1000 if self.etch_depth_nm else None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PDKLayer":
        """Create from dictionary."""
        return cls(**data)


# =============================================================================
# PDK Material
# =============================================================================

@dataclass
class PDKMaterial:
    """
    Material properties from a PDK.

    Supports both isotropic and anisotropic materials (e.g., Lithium Niobate).

    Attributes:
        name: Material name (e.g., "LN_Xcut", "Si", "SiN")
        n_ordinary: Ordinary refractive index
        n_extraordinary: Extraordinary refractive index (for anisotropic)
        is_anisotropic: Whether material is anisotropic
        crystal_cut: Crystal cut orientation ("X-cut", "Z-cut", etc.)
        wavelength_nm: Reference wavelength for refractive indices
        clad_n: Cladding refractive index (typically SiO2 ~1.44-1.47)
        description: Human-readable description
        sellmeier_coeffs: Optional Sellmeier coefficients for dispersion
    """
    name: str
    n_ordinary: float
    n_extraordinary: Optional[float] = None
    is_anisotropic: bool = False
    crystal_cut: Optional[str] = None
    wavelength_nm: float = 1550
    clad_n: float = 1.44
    description: str = ""
    sellmeier_coeffs: Optional[Dict[str, List[float]]] = None

    @property
    def n_core(self) -> float:
        """Return the primary core refractive index."""
        return self.n_ordinary

    @property
    def n_e(self) -> Optional[float]:
        """Alias for extraordinary index."""
        return self.n_extraordinary

    @property
    def n_o(self) -> float:
        """Alias for ordinary index."""
        return self.n_ordinary

    def get_index_at_wavelength(self, wavelength_nm: float) -> float:
        """
        Get refractive index at specified wavelength.
        Uses Sellmeier if available, otherwise returns reference value.
        """
        if self.sellmeier_coeffs:
            # Sellmeier equation implementation
            # n^2 - 1 = sum(B_i * lambda^2 / (lambda^2 - C_i))
            wl_um = wavelength_nm / 1000
            wl_sq = wl_um ** 2
            n_sq_minus_1 = 0

            B = self.sellmeier_coeffs.get("B", [])
            C = self.sellmeier_coeffs.get("C", [])

            for b, c in zip(B, C):
                n_sq_minus_1 += b * wl_sq / (wl_sq - c)

            return (n_sq_minus_1 + 1) ** 0.5

        return self.n_ordinary

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PDKMaterial":
        """Create from dictionary."""
        return cls(**data)


# =============================================================================
# PDK Cross-Section
# =============================================================================

@dataclass
class PDKCrossSection:
    """
    Cross-section geometry for a waveguide type.

    Defines the vertical structure of a waveguide including film thickness,
    etch depth, and resulting slab thickness.

    Attributes:
        name: Cross-section name (e.g., "WG1", "ridge", "rib")
        film_thickness_nm: Total film thickness before etching
        etch_depth_nm: Etch depth
        slab_thickness_nm: Remaining slab thickness (film - etch)
        sidewall_angle_deg: Sidewall angle in degrees
        material_name: Core material reference
        cladding_material: Cladding material name
        description: Human-readable description
    """
    name: str
    film_thickness_nm: float
    etch_depth_nm: float
    slab_thickness_nm: float
    sidewall_angle_deg: float
    material_name: str
    cladding_material: str = "SiO2"
    description: str = ""

    @property
    def is_fully_etched(self) -> bool:
        """Check if this is a fully etched (strip) waveguide."""
        return self.slab_thickness_nm <= 0

    @property
    def is_rib(self) -> bool:
        """Check if this is a rib/ridge waveguide."""
        return self.slab_thickness_nm > 0

    @property
    def film_thickness_um(self) -> float:
        """Film thickness in micrometers."""
        return self.film_thickness_nm / 1000

    @property
    def etch_depth_um(self) -> float:
        """Etch depth in micrometers."""
        return self.etch_depth_nm / 1000

    @property
    def slab_thickness_um(self) -> float:
        """Slab thickness in micrometers."""
        return self.slab_thickness_nm / 1000

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PDKCrossSection":
        """Create from dictionary."""
        return cls(**data)


# =============================================================================
# PDK Design Rule
# =============================================================================

@dataclass
class PDKDesignRule:
    """
    Design rule constraint from a PDK.

    Attributes:
        rule_name: Rule identifier (e.g., "min_width", "min_spacing")
        layer_name: Layer this rule applies to (None for global rules)
        min_value_um: Minimum value in micrometers
        max_value_um: Maximum value in micrometers
        description: Human-readable description
    """
    rule_name: str
    layer_name: Optional[str] = None
    min_value_um: Optional[float] = None
    max_value_um: Optional[float] = None
    description: str = ""

    @property
    def min_value_nm(self) -> Optional[float]:
        """Minimum value in nanometers."""
        return self.min_value_um * 1000 if self.min_value_um else None

    def check(self, value_um: float) -> bool:
        """Check if a value satisfies this rule."""
        if self.min_value_um is not None and value_um < self.min_value_um:
            return False
        if self.max_value_um is not None and value_um > self.max_value_um:
            return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PDKDesignRule":
        """Create from dictionary."""
        return cls(**data)


# =============================================================================
# PDK Definition (Complete PDK)
# =============================================================================

@dataclass
class PDKDefinition:
    """
    Complete PDK definition combining all elements.

    This is the main data structure representing a foundry's process design kit.

    Attributes:
        name: PDK name (e.g., "Generic Si 220nm")
        version: PDK version string
        foundry: Foundry name
        description: Human-readable description
        layers: Dictionary of layer definitions
        materials: Dictionary of material definitions
        cross_sections: Dictionary of cross-section definitions
        design_rules: List of design rules
        substrate_material: Substrate material (default "Si")
        box_thickness_um: Buried oxide thickness in micrometers
        source_pdf: Path to source PDF (if parsed from document)
        parsing_confidence: Confidence score from parsing (0-1)
    """
    name: str
    version: str = "1.0"
    foundry: str = ""
    description: str = ""

    # Core definitions (use field with default_factory for mutable defaults)
    layers: Dict[str, PDKLayer] = field(default_factory=dict)
    materials: Dict[str, PDKMaterial] = field(default_factory=dict)
    cross_sections: Dict[str, PDKCrossSection] = field(default_factory=dict)
    design_rules: List[PDKDesignRule] = field(default_factory=list)

    # Substrate/stack info
    substrate_material: str = "Si"
    box_thickness_um: float = 2.0

    # Parsing metadata
    source_pdf: Optional[str] = None
    parsing_confidence: float = 1.0

    # ==========================================================================
    # Layer Methods
    # ==========================================================================

    def get_layer(self, name: str) -> Optional[PDKLayer]:
        """Get layer by name."""
        return self.layers.get(name)

    def get_layer_by_gds(self, gds_number: int, datatype: int = 0) -> Optional[PDKLayer]:
        """Get layer by GDS number and datatype."""
        for layer in self.layers.values():
            if layer.gds_number == gds_number and layer.datatype == datatype:
                return layer
        return None

    def get_layers_by_purpose(self, purpose: str) -> List[PDKLayer]:
        """Get all layers with a specific purpose."""
        return [layer for layer in self.layers.values() if layer.purpose == purpose]

    def get_core_layers(self) -> List[PDKLayer]:
        """Get all core (waveguide) layers."""
        return self.get_layers_by_purpose(LayerPurpose.CORE)

    def get_metal_layers(self) -> List[PDKLayer]:
        """Get all metal layers."""
        return self.get_layers_by_purpose(LayerPurpose.METAL)

    # ==========================================================================
    # Material Methods
    # ==========================================================================

    def get_material(self, name: str) -> Optional[PDKMaterial]:
        """Get material by name."""
        return self.materials.get(name)

    def get_material_for_layer(self, layer_name: str) -> Optional[PDKMaterial]:
        """Get the material associated with a layer."""
        layer = self.get_layer(layer_name)
        if layer and layer.material_name:
            return self.get_material(layer.material_name)
        return None

    # ==========================================================================
    # Cross-Section Methods
    # ==========================================================================

    def get_cross_section(self, name: str) -> Optional[PDKCrossSection]:
        """Get cross-section by name."""
        return self.cross_sections.get(name)

    def get_cross_section_for_layer(self, layer_name: str) -> Optional[PDKCrossSection]:
        """Find a cross-section that matches a layer's etch depth."""
        layer = self.get_layer(layer_name)
        if not layer or not layer.etch_depth_nm:
            return None

        # Find cross-section with matching etch depth
        for xs in self.cross_sections.values():
            if abs(xs.etch_depth_nm - layer.etch_depth_nm) < 1:  # 1nm tolerance
                return xs

        return None

    # ==========================================================================
    # Serialization
    # ==========================================================================

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "version": self.version,
            "foundry": self.foundry,
            "description": self.description,
            "layers": {k: v.to_dict() for k, v in self.layers.items()},
            "materials": {k: v.to_dict() for k, v in self.materials.items()},
            "cross_sections": {k: v.to_dict() for k, v in self.cross_sections.items()},
            "design_rules": [r.to_dict() for r in self.design_rules],
            "substrate_material": self.substrate_material,
            "box_thickness_um": self.box_thickness_um,
            "source_pdf": self.source_pdf,
            "parsing_confidence": self.parsing_confidence,
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PDKDefinition":
        """Create from dictionary."""
        # Convert nested objects
        layers = {
            k: PDKLayer.from_dict(v)
            for k, v in data.get("layers", {}).items()
        }
        materials = {
            k: PDKMaterial.from_dict(v)
            for k, v in data.get("materials", {}).items()
        }
        cross_sections = {
            k: PDKCrossSection.from_dict(v)
            for k, v in data.get("cross_sections", {}).items()
        }
        design_rules = [
            PDKDesignRule.from_dict(r)
            for r in data.get("design_rules", [])
        ]

        return cls(
            name=data["name"],
            version=data.get("version", "1.0"),
            foundry=data.get("foundry", ""),
            description=data.get("description", ""),
            layers=layers,
            materials=materials,
            cross_sections=cross_sections,
            design_rules=design_rules,
            substrate_material=data.get("substrate_material", "Si"),
            box_thickness_um=data.get("box_thickness_um", 2.0),
            source_pdf=data.get("source_pdf"),
            parsing_confidence=data.get("parsing_confidence", 1.0),
        )

    @classmethod
    def from_json(cls, json_str: str) -> "PDKDefinition":
        """Create from JSON string."""
        return cls.from_dict(json.loads(json_str))

    @classmethod
    def load(cls, path: Path | str) -> "PDKDefinition":
        """Load PDK from JSON file."""
        path = Path(path)
        with open(path, "r") as f:
            return cls.from_json(f.read())

    def save(self, path: Path | str) -> None:
        """Save PDK to JSON file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            f.write(self.to_json())

    # ==========================================================================
    # Summary Methods
    # ==========================================================================

    def summary(self) -> str:
        """Return a human-readable summary of the PDK."""
        lines = [
            f"PDK: {self.name} v{self.version}",
            f"Foundry: {self.foundry}",
            f"Layers: {len(self.layers)}",
            f"Materials: {len(self.materials)}",
            f"Cross-sections: {len(self.cross_sections)}",
            f"Design rules: {len(self.design_rules)}",
        ]

        if self.layers:
            lines.append("\nLayers:")
            for layer in self.layers.values():
                mat = f" ({layer.material_name})" if layer.material_name else ""
                lines.append(f"  - {layer.name} (GDS {layer.gds_number}){mat}")

        if self.materials:
            lines.append("\nMaterials:")
            for mat in self.materials.values():
                if mat.is_anisotropic:
                    lines.append(f"  - {mat.name}: n_o={mat.n_ordinary:.4f}, n_e={mat.n_extraordinary:.4f}")
                else:
                    lines.append(f"  - {mat.name}: n={mat.n_ordinary:.4f}")

        return "\n".join(lines)

    def __repr__(self) -> str:
        return f"PDKDefinition(name='{self.name}', layers={len(self.layers)}, materials={len(self.materials)})"


# =============================================================================
# Layer Color Palette
# =============================================================================

# Default colors for different layer purposes
LAYER_COLORS = {
    LayerPurpose.CORE: "#2E86AB",      # Blue
    LayerPurpose.SLAB: "#A23B72",       # Purple
    LayerPurpose.METAL: "#F18F01",      # Orange
    LayerPurpose.VIA: "#C73E1D",        # Red
    LayerPurpose.HEATER: "#E63946",     # Bright red
    LayerPurpose.MARKER: "#808080",     # Gray
    LayerPurpose.PAD: "#FFD700",        # Gold
    LayerPurpose.TRENCH: "#4A4E69",     # Dark gray
    LayerPurpose.CLADDING: "#89CFF0",   # Light blue
}

def get_layer_color(purpose: str, index: int = 0) -> str:
    """Get a color for a layer based on purpose and index."""
    base_color = LAYER_COLORS.get(purpose, "#808080")
    # Could implement color variations based on index if needed
    return base_color
