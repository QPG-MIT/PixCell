"""
PDK to Tidy3D Converter

Converts PDK layer definitions to Tidy3D mediums and structures.
Handles isotropic and anisotropic materials (e.g., Lithium Niobate).
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

from .schema import PDKDefinition, PDKMaterial

# Conditional import for Tidy3D (may not be installed)
try:
    import tidy3d as td
    import numpy as np
    TIDY3D_AVAILABLE = True
except ImportError:
    TIDY3D_AVAILABLE = False
    td = None
    np = None


def is_tidy3d_available() -> bool:
    """Check if Tidy3D is available."""
    return TIDY3D_AVAILABLE


class PDKTidy3DConverter:
    """
    Converts PDK definitions to Tidy3D simulation elements.

    Handles:
    - Material → td.Medium / td.AnisotropicMedium
    - Layer + Cross-section → td.Structure with PolySlab geometry
    - Cladding/substrate mediums
    """

    def __init__(self, pdk: PDKDefinition):
        """
        Initialize converter with a PDK definition.

        Args:
            pdk: PDKDefinition to use for conversions
        """
        if not TIDY3D_AVAILABLE:
            raise RuntimeError(
                "Tidy3D is not installed. Install with: pip install 'pixcell[simulate]'"
            )

        self.pdk = pdk
        self._medium_cache: Dict[str, Any] = {}

    # =========================================================================
    # Material Conversion
    # =========================================================================

    def get_medium_for_material(
        self,
        material_name: str,
        wavelength_nm: Optional[float] = None,
        use_library: bool = False,
    ) -> "td.Medium | td.AnisotropicMedium":
        """
        Get Tidy3D medium for a PDK material.

        Args:
            material_name: Name of material in PDK
            wavelength_nm: Optional wavelength for dispersion (not yet implemented)
            use_library: If True, use Tidy3D's material library for LiNbO3 (better dispersion)

        Returns:
            td.Medium for isotropic, td.AnisotropicMedium for anisotropic

        Raises:
            KeyError: If material not found in PDK
        """
        # Check cache
        cache_key = f"{material_name}_{wavelength_nm or 'default'}_{use_library}"
        if cache_key in self._medium_cache:
            return self._medium_cache[cache_key]

        material = self.pdk.get_material(material_name)
        if not material:
            raise KeyError(f"Material '{material_name}' not found in PDK '{self.pdk.name}'")

        if material.is_anisotropic and material.n_extraordinary is not None:
            # Anisotropic material (e.g., Lithium Niobate)
            # Determine extraordinary axis from crystal cut
            crystal_cut = (material.crystal_cut or "").upper()

            if use_library and "LN" in material_name.upper() or "LINBO" in material_name.upper():
                # Use Tidy3D's built-in LiNbO3 model with proper dispersion
                # extraordinary_axis: 0=X, 1=Y, 2=Z
                if "Z" in crystal_cut:
                    extraordinary_axis = 2  # Z-cut: n_e along Z
                else:
                    extraordinary_axis = 1  # X-cut (default): n_e along Y
                medium = td.material_library['LiNbO3']['Zelmon1997'](extraordinary_axis)
            else:
                # Use PDK-specified refractive indices
                if "Z" in crystal_cut:
                    # Z-cut: extraordinary axis along Z (axis=2)
                    medium = td.AnisotropicMedium(
                        xx=td.Medium(permittivity=material.n_ordinary ** 2),
                        yy=td.Medium(permittivity=material.n_ordinary ** 2),
                        zz=td.Medium(permittivity=material.n_extraordinary ** 2),
                    )
                else:
                    # X-cut (default): extraordinary axis along Y (axis=1)
                    medium = td.AnisotropicMedium(
                        xx=td.Medium(permittivity=material.n_ordinary ** 2),
                        yy=td.Medium(permittivity=material.n_extraordinary ** 2),
                        zz=td.Medium(permittivity=material.n_ordinary ** 2),
                    )
        else:
            # Isotropic material
            medium = td.Medium(permittivity=material.n_ordinary ** 2)

        self._medium_cache[cache_key] = medium
        return medium

    def get_medium_for_layer(
        self,
        layer_name: str,
        wavelength_nm: Optional[float] = None
    ) -> "td.Medium | td.AnisotropicMedium":
        """
        Get Tidy3D medium for a PDK layer.

        Args:
            layer_name: Name of layer in PDK
            wavelength_nm: Optional wavelength for dispersion

        Returns:
            Tidy3D medium object

        Raises:
            KeyError: If layer or its material not found
        """
        layer = self.pdk.get_layer(layer_name)
        if not layer:
            raise KeyError(f"Layer '{layer_name}' not found in PDK '{self.pdk.name}'")

        if not layer.material_name:
            raise ValueError(f"Layer '{layer_name}' has no material assigned")

        return self.get_medium_for_material(layer.material_name, wavelength_nm)

    def get_cladding_medium(
        self,
        material_name: Optional[str] = None
    ) -> "td.Medium":
        """
        Get cladding medium.

        Args:
            material_name: Optional specific cladding material name

        Returns:
            td.Medium for cladding (typically SiO2)
        """
        if material_name and material_name in self.pdk.materials:
            material = self.pdk.materials[material_name]
            return td.Medium(permittivity=material.n_ordinary ** 2)

        # Default: use first core layer's material clad_n
        for mat in self.pdk.materials.values():
            if mat.clad_n:
                return td.Medium(permittivity=mat.clad_n ** 2)

        # Fallback: SiO2 at 1550nm
        return td.Medium(permittivity=1.44 ** 2)

    def get_substrate_medium(self) -> "td.Medium":
        """
        Get substrate medium.

        Returns:
            td.Medium for substrate (typically Si)
        """
        if self.pdk.substrate_material == "Si":
            return td.Medium(permittivity=3.47 ** 2)
        elif self.pdk.substrate_material in self.pdk.materials:
            mat = self.pdk.materials[self.pdk.substrate_material]
            return td.Medium(permittivity=mat.n_ordinary ** 2)
        else:
            # Fallback: silicon
            return td.Medium(permittivity=3.47 ** 2)

    # =========================================================================
    # Structure Creation
    # =========================================================================

    def create_polyslab_structure(
        self,
        vertices: List[Tuple[float, float]],
        layer_name: str,
        cross_section_name: Optional[str] = None,
        z_base: float = 0.0,
        name: Optional[str] = None,
    ) -> "td.Structure":
        """
        Create a Tidy3D Structure with PolySlab geometry from PDK layer.

        Args:
            vertices: List of (x, y) coordinates in micrometers defining the polygon
            layer_name: PDK layer name for material properties
            cross_section_name: Optional cross-section name for geometry params
            z_base: Z position of the base of the structure (um)
            name: Optional name for the structure

        Returns:
            td.Structure with PolySlab geometry and appropriate medium
        """
        layer = self.pdk.get_layer(layer_name)
        if not layer:
            raise KeyError(f"Layer '{layer_name}' not found in PDK")

        medium = self.get_medium_for_layer(layer_name)

        # Get geometry parameters
        if cross_section_name:
            xs = self.pdk.get_cross_section(cross_section_name)
            if xs:
                thickness_um = xs.film_thickness_nm / 1000
                # FIXED: Tidy3D sidewall_angle is measured from normal/vertical
                # No transformation needed - use angle directly
                sidewall_angle_rad = math.radians(xs.sidewall_angle_deg)
            else:
                thickness_um = (layer.thickness_nm or 220) / 1000
                # Default to 0 (vertical) if not specified
                sidewall_angle_rad = math.radians(layer.sidewall_angle_deg or 0)
        else:
            # Use layer defaults
            thickness_um = (layer.thickness_nm or 220) / 1000
            # Default to 0 (vertical) if not specified
            sidewall_angle_rad = math.radians(layer.sidewall_angle_deg or 0)

        # Create PolySlab geometry
        # Tidy3D sidewall_angle: 0 = vertical, positive = angled outward from normal
        # reference_plane="bottom" matches reference implementation convention
        geometry = td.PolySlab(
            vertices=vertices,
            slab_bounds=(z_base, z_base + thickness_um),
            sidewall_angle=sidewall_angle_rad,
            reference_plane="bottom",
        )

        return td.Structure(
            geometry=geometry,
            medium=medium,
            name=name,
        )

    def create_box_structure(
        self,
        bounds: Tuple[Tuple[float, float, float], Tuple[float, float, float]],
        name: str = "box",
    ) -> "td.Structure":
        """
        Create BOX (buried oxide) structure.

        Args:
            bounds: ((x_min, y_min, z_min), (x_max, y_max, z_max)) in um
            name: Structure name

        Returns:
            td.Structure for the buried oxide layer
        """
        geometry = td.Box(
            center=(
                (bounds[0][0] + bounds[1][0]) / 2,
                (bounds[0][1] + bounds[1][1]) / 2,
                (bounds[0][2] + bounds[1][2]) / 2,
            ),
            size=(
                bounds[1][0] - bounds[0][0],
                bounds[1][1] - bounds[0][1],
                bounds[1][2] - bounds[0][2],
            ),
        )

        return td.Structure(
            geometry=geometry,
            medium=self.get_cladding_medium(),
            name=name,
        )

    # =========================================================================
    # Layer Info Export
    # =========================================================================

    def get_layer_simulation_info(self, layer_name: str) -> Dict[str, Any]:
        """
        Get simulation-relevant information for a layer.

        Args:
            layer_name: PDK layer name

        Returns:
            Dictionary with material properties and geometry info
        """
        layer = self.pdk.get_layer(layer_name)
        if not layer:
            return {}

        info = {
            "layer_name": layer_name,
            "gds_layer": layer.gds_number,
            "gds_datatype": layer.datatype,
            "purpose": layer.purpose,
        }

        # Add geometry info
        if layer.thickness_nm:
            info["thickness_nm"] = layer.thickness_nm
            info["thickness_um"] = layer.thickness_nm / 1000
        if layer.etch_depth_nm:
            info["etch_depth_nm"] = layer.etch_depth_nm
        if layer.sidewall_angle_deg:
            info["sidewall_angle_deg"] = layer.sidewall_angle_deg

        # Add material info
        if layer.material_name:
            material = self.pdk.get_material(layer.material_name)
            if material:
                info["material_name"] = material.name
                info["n_ordinary"] = material.n_ordinary
                info["is_anisotropic"] = material.is_anisotropic
                if material.is_anisotropic:
                    info["n_extraordinary"] = material.n_extraordinary
                    info["crystal_cut"] = material.crystal_cut
                if material.clad_n:
                    info["clad_n"] = material.clad_n

        return info

    def get_all_layers_info(self) -> Dict[str, Dict[str, Any]]:
        """Get simulation info for all layers in PDK."""
        return {
            name: self.get_layer_simulation_info(name)
            for name in self.pdk.layers.keys()
        }


# =============================================================================
# Convenience Functions
# =============================================================================

def create_medium_from_pdk_material(material: PDKMaterial) -> "td.Medium | td.AnisotropicMedium":
    """
    Create Tidy3D medium from a PDKMaterial object.

    Args:
        material: PDKMaterial definition

    Returns:
        Tidy3D medium object
    """
    if not TIDY3D_AVAILABLE:
        raise RuntimeError("Tidy3D is not installed")

    if material.is_anisotropic and material.n_extraordinary is not None:
        # Determine extraordinary axis from crystal cut
        crystal_cut = (material.crystal_cut or "").upper()

        if "Z" in crystal_cut:
            # Z-cut: extraordinary axis along Z
            return td.AnisotropicMedium(
                xx=td.Medium(permittivity=material.n_ordinary ** 2),
                yy=td.Medium(permittivity=material.n_ordinary ** 2),
                zz=td.Medium(permittivity=material.n_extraordinary ** 2),
            )
        else:
            # X-cut (default): extraordinary axis along Y
            return td.AnisotropicMedium(
                xx=td.Medium(permittivity=material.n_ordinary ** 2),
                yy=td.Medium(permittivity=material.n_extraordinary ** 2),
                zz=td.Medium(permittivity=material.n_ordinary ** 2),
            )
    else:
        return td.Medium(permittivity=material.n_ordinary ** 2)


def get_linbo3_from_library(
    crystal_cut: str = "X-cut",
    model: str = "Zelmon1997",
) -> "td.AnisotropicMedium":
    """
    Get LiNbO3 medium from Tidy3D's built-in material library.

    This provides accurate dispersion modeling across wavelengths.

    Args:
        crystal_cut: Crystal orientation - "X-cut" or "Z-cut"
        model: Material model name (default: "Zelmon1997")

    Returns:
        td.AnisotropicMedium with proper dispersion

    Example:
        >>> ln = get_linbo3_from_library("X-cut")  # n_e along Y
        >>> ln = get_linbo3_from_library("Z-cut")  # n_e along Z
    """
    if not TIDY3D_AVAILABLE:
        raise RuntimeError("Tidy3D is not installed")

    # extraordinary_axis: 0=X, 1=Y, 2=Z
    if "Z" in crystal_cut.upper():
        extraordinary_axis = 2  # Z-cut: n_e along Z
    else:
        extraordinary_axis = 1  # X-cut: n_e along Y

    return td.material_library['LiNbO3'][model](extraordinary_axis)


def get_material_preset_from_pdk(
    pdk: PDKDefinition,
    layer_name: str,
) -> Dict[str, Any]:
    """
    Get material preset dictionary (compatible with Flex MATERIAL_PRESETS format).

    Args:
        pdk: PDK definition
        layer_name: Layer name to get preset for

    Returns:
        Dictionary compatible with Flex MATERIAL_PRESETS
    """
    layer = pdk.get_layer(layer_name)
    if not layer or not layer.material_name:
        return {}

    material = pdk.get_material(layer.material_name)
    if not material:
        return {}

    if material.is_anisotropic:
        return {
            "n_e": material.n_extraordinary,
            "n_o": material.n_ordinary,
            "clad_n": material.clad_n,
            "default_thickness_nm": layer.thickness_nm or 400,
            "anisotropic": True,
            "description": f"{pdk.name} - {layer.name}",
        }
    else:
        return {
            "core_n": material.n_ordinary,
            "clad_n": material.clad_n,
            "default_thickness_nm": layer.thickness_nm or 220,
            "anisotropic": False,
            "description": f"{pdk.name} - {layer.name}",
        }
