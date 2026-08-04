"""
Flex Materials Module

Material presets and Tidy3D medium creation for photonic simulations.
"""

from typing import Dict, Any, Optional

# Check if Tidy3D is available
try:
    import tidy3d as td
    TIDY3D_AVAILABLE = True
except ImportError:
    TIDY3D_AVAILABLE = False
    td = None


# =============================================================================
# MATERIAL PRESETS
# =============================================================================

MATERIAL_PRESETS: Dict[str, Dict[str, Any]] = {
    "Silicon (SOI)": {
        "core_n": 3.47,
        "clad_n": 1.47,
        "default_thickness_nm": 220,
        "anisotropic": False,
        "description": "Standard silicon-on-insulator platform (220nm SOI)",
        # Single-mode dimension constraints (at 1550nm)
        "single_mode_width_nm": 500,   # Max width for single-mode at 220nm height
        "single_mode_height_nm": 220,  # Standard SOI thickness
        "max_dimension_for_single_mode": 500,  # nm
        # Sellmeier coefficients for Si at 1550nm
        "dispersion_model": "sellmeier",
        "sellmeier_coefficients": {
            "A": 10.668,
            "B": 0.003043,
            "C": 1.5413,
            "wavelength_range_um": (1.1, 1.7),
        },
    },
    "Lithium Niobate": {
        "n_e": 2.138,  # extraordinary axis (Y for X-cut)
        "n_o": 2.211,  # ordinary axis (X, Z for X-cut)
        "clad_n": 1.44,
        "default_thickness_nm": 400,
        "anisotropic": True,
        "description": "Thin-film LN for electro-optic devices (X-cut)",
        # Single-mode dimension constraints (at 1550nm)
        "single_mode_width_nm": 1000,
        "single_mode_height_nm": 400,
        "max_dimension_for_single_mode": 1000,  # nm
        # Sellmeier coefficients for LN e-ray
        "dispersion_model": "sellmeier",
        "sellmeier_coefficients": {
            "A": 4.582,
            "B": 0.099,
            "C": 0.044,
            "wavelength_range_um": (0.4, 5.0),
        },
    },
    "Silicon Nitride": {
        "core_n": 2.0,
        "clad_n": 1.47,
        "default_thickness_nm": 400,
        "anisotropic": False,
        "description": "Low-loss SiN platform for visible/NIR",
        # Single-mode dimension constraints (at 1550nm)
        "single_mode_width_nm": 1000,
        "single_mode_height_nm": 400,
        "max_dimension_for_single_mode": 1000,  # nm
        # Sellmeier coefficients for Si3N4
        "dispersion_model": "sellmeier",
        "sellmeier_coefficients": {
            "A": 3.0,
            "B": 0.04,
            "C": 0.14,
            "wavelength_range_um": (0.4, 2.0),
        },
    },
    "Custom": {
        "core_n": 2.5,
        "clad_n": 1.45,
        "default_thickness_nm": 300,
        "anisotropic": False,
        "description": "User-defined material properties",
        # Single-mode guidance for custom materials
        "single_mode_width_nm": None,  # User must calculate
        "single_mode_height_nm": None,
        "max_dimension_for_single_mode": None,
        # No dispersion model by default
        "dispersion_model": "constant",
        "sellmeier_coefficients": None,
    }
}


def get_material_preset(name: str) -> Dict[str, Any]:
    """
    Get a material preset by name.

    Args:
        name: Preset name (e.g., "Silicon (SOI)")

    Returns:
        Material preset dictionary

    Raises:
        KeyError: If preset not found
    """
    if name not in MATERIAL_PRESETS:
        raise KeyError(f"Unknown material preset: {name}. Available: {list(MATERIAL_PRESETS.keys())}")
    return MATERIAL_PRESETS[name].copy()


def get_material_medium(n: float):
    """
    Create a Tidy3D Medium from refractive index.

    Args:
        n: Refractive index

    Returns:
        td.Medium object

    Raises:
        RuntimeError: If Tidy3D not available
    """
    if not TIDY3D_AVAILABLE:
        raise RuntimeError("Tidy3D is not installed. Install with: pip install 'pixcell[simulate]'")

    return td.Medium(permittivity=n**2)


def get_cladding_medium(n: float):
    """
    Create a Tidy3D Medium for cladding material.

    Args:
        n: Cladding refractive index

    Returns:
        td.Medium object
    """
    return get_material_medium(n)


def get_anisotropic_medium(n_o: float, n_e: float):
    """
    Create an anisotropic medium for materials like Lithium Niobate.

    Uses X-cut orientation where:
    - n_o (ordinary) applies to X and Z axes
    - n_e (extraordinary) applies to Y axis

    Args:
        n_o: Ordinary refractive index
        n_e: Extraordinary refractive index

    Returns:
        td.AnisotropicMedium object
    """
    if not TIDY3D_AVAILABLE:
        raise RuntimeError("Tidy3D is not installed. Install with: pip install 'pixcell[simulate]'")

    # X-cut orientation: n_o in X,Z planes, n_e in Y
    return td.AnisotropicMedium(
        xx=td.Medium(permittivity=n_o**2),
        yy=td.Medium(permittivity=n_e**2),
        zz=td.Medium(permittivity=n_o**2)
    )


def create_material_from_preset(
    preset_name: str,
    custom_core_n: Optional[float] = None,
    custom_clad_n: Optional[float] = None
) -> tuple:
    """
    Create core and cladding media from a preset.

    Args:
        preset_name: Name of the material preset
        custom_core_n: Override core index (for Custom preset)
        custom_clad_n: Override cladding index (for Custom preset)

    Returns:
        Tuple of (core_medium, clad_medium, preset_info)
    """
    if not TIDY3D_AVAILABLE:
        raise RuntimeError("Tidy3D is not installed. Install with: pip install 'pixcell[simulate]'")

    preset = get_material_preset(preset_name)

    # Handle custom material
    if preset_name == "Custom":
        core_n = custom_core_n if custom_core_n is not None else preset["core_n"]
        clad_n = custom_clad_n if custom_clad_n is not None else preset["clad_n"]
        core_medium = get_material_medium(core_n)
        clad_medium = get_cladding_medium(clad_n)
    # Handle anisotropic materials
    elif preset.get("anisotropic", False):
        core_medium = get_anisotropic_medium(preset["n_o"], preset["n_e"])
        clad_medium = get_cladding_medium(preset["clad_n"])
    # Handle isotropic materials
    else:
        core_medium = get_material_medium(preset["core_n"])
        clad_medium = get_cladding_medium(preset["clad_n"])

    return core_medium, clad_medium, preset


def is_available() -> bool:
    """Check if Tidy3D is available."""
    return TIDY3D_AVAILABLE
