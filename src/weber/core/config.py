"""
Weber Configuration

Handles API keys, paths, and other configuration settings.
"""

import os
from pathlib import Path
from typing import Optional


# =============================================================================
# PATHS
# =============================================================================

# Weber root directory
WEBER_ROOT = Path(__file__).parent.parent

# Template files directory
TEMPLATES_DIR = WEBER_ROOT / "templates"

# Output directory for generated explorers
OUTPUT_DIR = WEBER_ROOT / "output"

# Cache directory for agent responses
CACHE_DIR = WEBER_ROOT / ".weber_cache"


# =============================================================================
# API KEYS
# =============================================================================

def get_anthropic_api_key(override: Optional[str] = None) -> Optional[str]:
    """
    Get Anthropic API key from environment or override.

    Args:
        override: Direct API key value (takes precedence)

    Returns:
        API key string or None if not found
    """
    if override:
        return override
    return os.environ.get("ANTHROPIC_API_KEY")


def get_tidy3d_api_key(override: Optional[str] = None) -> Optional[str]:
    """
    Get Tidy3D API key from environment or override.

    Args:
        override: Direct API key value (takes precedence)

    Returns:
        API key string or None if not found
    """
    if override:
        return override
    return os.environ.get("TIDY3D_API_KEY") or os.environ.get("SIMCLOUD_APIKEY")


# =============================================================================
# COMPONENT SWAPPING CONFIGURATION
# =============================================================================

# Groups of components that can be swapped for each other
# Only components with compatible parameter signatures should be grouped
SWAP_GROUPS = {
    "shapes": ["rectangle", "circle", "ellipse", "triangle"],
    # bend_circular and bend_euler both use radius/angle parameters
    "bends_radius": ["bend_circular", "bend_euler"],
    # bend_s uses size=(dx, dy) - not compatible with radius-based bends
    "bends_size": ["bend_s"],
    "waveguides": ["straight", "taper"],
}


def get_swappable_types(comp_type: str) -> list:
    """
    Get list of component types that can replace the given type.

    Args:
        comp_type: Component type name (e.g., "rectangle", "bend_circular")

    Returns:
        List of swappable type names
    """
    for group in SWAP_GROUPS.values():
        if comp_type in group:
            return group.copy()
    return [comp_type]  # No alternatives, only itself


# =============================================================================
# PARAMETER EXTRACTION CONFIGURATION
# =============================================================================

# Parameter names that should be skipped (not exposed as sliders)
SKIP_PARAMETER_NAMES = {
    "layer",
    "datatype",
    "centered",
    "port",
    "ports",
    "name",
    "cross_section",
}

# Parameter value ranges that indicate non-tunable values
SKIP_VALUE_PATTERNS = {
    # Layer numbers (typically 0-255)
    "layer_range": (0, 255),
    # Datatype (typically 0-255)
    "datatype_range": (0, 255),
}


def should_skip_parameter(name: str, value: any) -> bool:
    """
    Determine if a parameter should be skipped (not exposed as slider).

    Args:
        name: Parameter name
        value: Parameter value

    Returns:
        True if parameter should be skipped
    """
    # Check name-based skipping
    if name.lower() in SKIP_PARAMETER_NAMES:
        return True

    # Check if it looks like a layer tuple
    if isinstance(value, tuple) and len(value) == 2:
        if all(isinstance(v, int) and 0 <= v <= 255 for v in value):
            return True

    return False


# =============================================================================
# SLIDER RANGE HEURISTICS
# =============================================================================

def suggest_slider_range(value: float, name: str = "") -> tuple:
    """
    Suggest min/max/step for a slider based on the current value.

    Args:
        value: Current parameter value
        name: Parameter name (optional, for context)

    Returns:
        Tuple of (min_value, max_value, step)
    """
    if value == 0:
        return (0.0, 1.0, 0.1)

    # Negative values
    if value < 0:
        return (value * 3, -value * 0.2, abs(value) / 20)

    # Angles (if name suggests it)
    name_lower = name.lower()
    if "angle" in name_lower:
        return (1, 360, 1)

    # Small values (< 0.1) - likely fine features
    if value < 0.1:
        return (value * 0.2, value * 5, value / 10)

    # Normal values
    min_val = max(0.01, value * 0.2)
    max_val = value * 3
    step = value / 20

    # Round step to reasonable precision
    if step >= 1:
        step = round(step)
    elif step >= 0.1:
        step = round(step, 1)
    else:
        step = round(step, 2)

    return (round(min_val, 3), round(max_val, 3), step)
