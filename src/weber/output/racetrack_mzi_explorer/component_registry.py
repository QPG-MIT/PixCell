"""
Component Registry - Defines all available component types and their parameters.

Each component type is registered with:
- Factory function (GDSFactory call)
- Parameter specifications (min, max, default, step)
- Port information
- Category (basic_shape, waveguide, bend)
"""

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Any, Tuple, Optional
import gdsfactory as gf


@dataclass
class ParameterSpec:
    """Specification for a single component parameter."""
    name: str                  # Parameter name (used in code)
    label: str                 # Display label (shown in UI)
    min_value: float           # Slider minimum
    max_value: float           # Slider maximum
    default_value: float       # Default value
    step: float                # Slider step
    unit: str = "um"           # Display unit
    help_text: str = ""        # Tooltip help text


@dataclass
class ComponentSpec:
    """Specification for a component type."""
    name: str                              # Internal name (registry key)
    display_name: str                      # UI display name
    category: str                          # "basic_shape" | "waveguide" | "bend"
    parameters: List[ParameterSpec]        # List of tunable parameters
    has_ports: bool = True                 # Whether component exposes ports
    output_ports: List[str] = field(default_factory=lambda: ["o1", "o2"])
    notes: str = ""                        # Implementation notes


# =============================================================================
# COMPONENT REGISTRY
# =============================================================================

COMPONENT_REGISTRY: Dict[str, ComponentSpec] = {}

# -----------------------------------------------------------------------------
# Basic Shapes (no ports, for pads/holes)
# -----------------------------------------------------------------------------

COMPONENT_REGISTRY["rectangle"] = ComponentSpec(
    name="rectangle",
    display_name="Rectangle",
    category="basic_shape",
    has_ports=False,
    output_ports=[],
    parameters=[
        ParameterSpec("width", "Width", 0.1, 3.0, 0.6, 0.05, "um", "Rectangle width"),
        ParameterSpec("height", "Height", 0.1, 3.0, 0.75, 0.05, "um", "Rectangle height"),
    ]
)

COMPONENT_REGISTRY["circle"] = ComponentSpec(
    name="circle",
    display_name="Circle",
    category="basic_shape",
    has_ports=False,
    output_ports=[],
    parameters=[
        ParameterSpec("radius", "Radius", 0.05, 2.0, 0.3, 0.02, "um", "Circle radius"),
    ]
)

COMPONENT_REGISTRY["ellipse"] = ComponentSpec(
    name="ellipse",
    display_name="Ellipse",
    category="basic_shape",
    has_ports=False,
    output_ports=[],
    parameters=[
        ParameterSpec("rx", "X Radius", 0.05, 2.0, 0.3, 0.02, "um", "Horizontal radius"),
        ParameterSpec("ry", "Y Radius", 0.05, 2.0, 0.4, 0.02, "um", "Vertical radius"),
    ]
)

COMPONENT_REGISTRY["triangle"] = ComponentSpec(
    name="triangle",
    display_name="Triangle",
    category="basic_shape",
    has_ports=False,
    output_ports=[],
    parameters=[
        ParameterSpec("x", "Base (X)", 0.1, 2.0, 0.5, 0.02, "um", "Triangle base width"),
        ParameterSpec("y", "Height (Y)", 0.1, 2.0, 0.5, 0.02, "um", "Triangle height"),
    ]
)

# -----------------------------------------------------------------------------
# Waveguide Types (with ports, for straights/arms)
# -----------------------------------------------------------------------------

COMPONENT_REGISTRY["straight"] = ComponentSpec(
    name="straight",
    display_name="Straight Waveguide",
    category="waveguide",
    has_ports=True,
    output_ports=["o1", "o2"],
    parameters=[
        ParameterSpec("length", "Length", 0.1, 10.0, 2.5, 0.1, "um", "Waveguide length"),
        ParameterSpec("width", "Width", 0.1, 2.0, 0.5, 0.02, "um", "Waveguide width"),
    ]
)

COMPONENT_REGISTRY["taper"] = ComponentSpec(
    name="taper",
    display_name="Taper",
    category="waveguide",
    has_ports=True,
    output_ports=["o1", "o2"],
    parameters=[
        ParameterSpec("length", "Length", 0.1, 5.0, 1.0, 0.05, "um", "Taper length"),
        ParameterSpec("width1", "Input Width", 0.1, 2.0, 0.5, 0.02, "um", "Width at input"),
        ParameterSpec("width2", "Output Width", 0.1, 2.0, 1.0, 0.02, "um", "Width at output"),
    ]
)

# -----------------------------------------------------------------------------
# Bend Types (with ports, for ring bends and connectors)
# -----------------------------------------------------------------------------

COMPONENT_REGISTRY["bend_s"] = ComponentSpec(
    name="bend_s",
    display_name="S-Bend",
    category="bend",
    has_ports=True,
    output_ports=["o1", "o2"],
    parameters=[
        ParameterSpec("dx", "Horizontal (dx)", 0.1, 3.0, 0.5, 0.02, "um", "Horizontal distance"),
        ParameterSpec("dy", "Vertical (dy)", -2.0, 2.0, 0.3, 0.02, "um", "Vertical offset"),
        ParameterSpec("width", "Width", 0.1, 1.0, 0.3, 0.02, "um", "Waveguide width"),
    ]
)

COMPONENT_REGISTRY["bend_euler"] = ComponentSpec(
    name="bend_euler",
    display_name="Euler Bend",
    category="bend",
    has_ports=True,
    output_ports=["o1", "o2"],
    parameters=[
        ParameterSpec("radius", "Radius", 0.5, 5.0, 1.1, 0.05, "um", "Bend radius"),
        ParameterSpec("angle", "Angle", 1, 180, 180, 1, "deg", "Bend angle in degrees"),
        ParameterSpec("width", "Width", 0.1, 2.0, 0.8, 0.02, "um", "Waveguide width"),
    ]
)

COMPONENT_REGISTRY["bend_circular"] = ComponentSpec(
    name="bend_circular",
    display_name="Circular Bend",
    category="bend",
    has_ports=True,
    output_ports=["o1", "o2"],
    parameters=[
        ParameterSpec("radius", "Radius", 0.5, 5.0, 1.1, 0.05, "um", "Bend radius"),
        ParameterSpec("angle", "Angle", 1, 180, 180, 1, "deg", "Bend angle in degrees"),
        ParameterSpec("width", "Width", 0.1, 2.0, 0.8, 0.02, "um", "Waveguide width"),
    ]
)


# =============================================================================
# FACTORY FUNCTIONS
# =============================================================================

def create_component(
    comp_type: str,
    params: Dict[str, Any],
    layer: Tuple[int, int] = (1, 0)
) -> gf.Component:
    """
    Universal component factory that creates GDSFactory components.

    Args:
        comp_type: Registry key for component type
        params: Dictionary of parameter values
        layer: GDS layer tuple (layer, datatype)

    Returns:
        GDSFactory Component
    """
    spec = COMPONENT_REGISTRY.get(comp_type)
    if not spec:
        raise ValueError(f"Unknown component type: {comp_type}")

    if spec.category == "basic_shape":
        return _create_basic_shape(comp_type, params, layer)
    elif spec.category in ("waveguide", "bend"):
        return _create_waveguide(comp_type, params, layer)
    else:
        raise ValueError(f"Unknown category: {spec.category}")


def _create_basic_shape(
    comp_type: str,
    params: Dict[str, Any],
    layer: Tuple[int, int]
) -> gf.Component:
    """Create basic shape components (rectangle, circle, etc.)"""

    if comp_type == "rectangle":
        return gf.components.rectangle(
            size=(params.get("width", 0.6), params.get("height", 0.75)),
            layer=layer,
            centered=True
        )
    elif comp_type == "circle":
        return gf.components.circle(
            radius=params.get("radius", 0.3),
            layer=layer
        )
    elif comp_type == "ellipse":
        return gf.components.ellipse(
            radii=(params.get("rx", 0.3), params.get("ry", 0.4)),
            layer=layer
        )
    elif comp_type == "triangle":
        return gf.components.triangle(
            x=params.get("x", 0.5),
            y=params.get("y", 0.5),
            layer=layer
        )
    else:
        raise ValueError(f"Unknown basic shape: {comp_type}")


def _create_waveguide(
    comp_type: str,
    params: Dict[str, Any],
    layer: Tuple[int, int]
) -> gf.Component:
    """Create waveguide/bend components with cross_section."""

    width = params.get("width", 0.5)

    if comp_type == "straight":
        xs = gf.cross_section.cross_section(width=width, layer=layer, radius=1.0)
        return gf.components.straight(
            length=params.get("length", 2.5),
            cross_section=xs
        )

    elif comp_type == "taper":
        return gf.components.taper(
            length=params.get("length", 1.0),
            width1=params.get("width1", 0.5),
            width2=params.get("width2", 1.0),
            layer=layer
        )

    elif comp_type == "bend_s":
        xs = gf.cross_section.cross_section(width=width, layer=layer, radius=0.1)
        return gf.components.bend_s(
            size=(params.get("dx", 0.5), params.get("dy", 0.3)),
            cross_section=xs
        )

    elif comp_type == "bend_euler":
        radius = params.get("radius", 1.1)
        xs = gf.cross_section.cross_section(width=width, layer=layer, radius=radius)
        return gf.components.bend_euler(
            radius=radius,
            angle=params.get("angle", 180),
            cross_section=xs
        )

    elif comp_type == "bend_circular":
        radius = params.get("radius", 1.1)
        xs = gf.cross_section.cross_section(width=width, layer=layer, radius=radius)
        return gf.components.bend_circular(
            radius=radius,
            angle=params.get("angle", 180),
            cross_section=xs
        )

    else:
        raise ValueError(f"Unknown waveguide type: {comp_type}")


def get_default_params(comp_type: str) -> Dict[str, float]:
    """Get default parameters for a component type."""
    spec = COMPONENT_REGISTRY.get(comp_type)
    if not spec:
        return {}
    return {p.name: p.default_value for p in spec.parameters}


def get_component_types_by_category(category: str) -> List[str]:
    """Get all component types in a category."""
    return [
        name for name, spec in COMPONENT_REGISTRY.items()
        if spec.category == category
    ]


def get_all_basic_shapes() -> List[str]:
    """Get all basic shape component types."""
    return get_component_types_by_category("basic_shape")


def get_all_waveguides() -> List[str]:
    """Get all waveguide component types (including bends)."""
    return (
        get_component_types_by_category("waveguide") +
        get_component_types_by_category("bend")
    )


# =============================================================================
# SWAPPABLE TYPE GROUPS
# =============================================================================

SWAP_GROUPS = {
    "shapes": ["rectangle", "circle", "ellipse", "triangle"],
    "bends": ["bend_circular", "bend_euler", "bend_s"],
    "waveguides": ["straight", "taper"],
}


def get_swappable_types(comp_type: str) -> List[str]:
    """Return list of types that this component can be swapped with."""
    for group in SWAP_GROUPS.values():
        if comp_type in group:
            return group
    return [comp_type]  # No alternatives
