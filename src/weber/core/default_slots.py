"""
Weber Default Slots Generator

Generates smart default slot configurations when the AI agent is skipped.
Provides full functionality (parameterization, swapping, layer assignment)
using heuristics and pattern matching.
"""

import json
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple
from .analyzer import ScriptAnalysis, ComponentInfo
from .config import get_swappable_types, should_skip_parameter


@dataclass
class SlotParameter:
    """Parameter definition for a slot."""
    name: str
    label: str
    min_value: float
    max_value: float
    default_value: float
    step: float
    unit: str = "um"


@dataclass
class SlotDefinition:
    """Definition of a single slot in the device."""
    slot_id: str
    display_name: str
    component_ids: List[str]
    current_type: str
    allowed_types: List[str]
    category: str
    parameters: List[SlotParameter]
    layer_group: Optional[str] = None


@dataclass
class LayerGroup:
    """Definition of a layer group for UI organization."""
    name: str
    slot_ids: List[str]
    default_layer: Tuple[int, int]
    color: str = "#2E86AB"


@dataclass
class GlobalParameter:
    """Global parameter that affects multiple slots."""
    name: str
    label: str
    affects: List[str]
    min_value: float
    max_value: float
    default_value: float
    step: float


@dataclass
class SlotConfig:
    """Complete slot configuration for a device."""
    slots: List[SlotDefinition]
    layer_groups: List[LayerGroup]
    global_params: List[GlobalParameter]

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(asdict(self), indent=2)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_json(cls, json_str: str) -> "SlotConfig":
        """Deserialize from JSON string."""
        data = json.loads(json_str)
        return cls(
            slots=[SlotDefinition(**s) for s in data.get("slots", [])],
            layer_groups=[LayerGroup(**lg) for lg in data.get("layer_groups", [])],
            global_params=[GlobalParameter(**gp) for gp in data.get("global_params", [])]
        )


def infer_category(comp: ComponentInfo) -> str:
    """Infer the category of a component based on its type and name."""
    comp_type = comp.type.lower()
    comp_id = comp.id.lower()

    # First, try to infer from component ID (more semantic)
    # Ring-related
    if "ring" in comp_id:
        if "straight" in comp_type:
            return "ring_straight"
        if "bend" in comp_type:
            return "ring_bend"
        return "ring"

    # Arm-related
    if "arm" in comp_id:
        return "arm"

    # Block/pad-related
    if "block" in comp_id or "pad" in comp_id:
        return "block"

    # Connector/s-bend related
    if "connector" in comp_id or "sbend" in comp_id or "s_bend" in comp_id:
        return "connector"

    # Taper-related
    if "taper" in comp_id:
        return "taper"

    # Hole-related
    if "hole" in comp_id or "cutout" in comp_id:
        return "hole"

    # Fall back to type-based inference
    # Basic shapes
    if comp_type in ["rectangle", "circle", "ellipse", "triangle"]:
        return "shape"

    # Bends
    if "bend" in comp_type:
        return "bend"

    # Waveguides
    if comp_type in ["straight", "taper", "waveguide"]:
        return "waveguide"

    # Path-based
    if "path" in comp_type or "route" in comp_type:
        return "path"

    # Boolean operations
    if comp_type == "boolean":
        return "boolean"

    return "other"


def generate_slot_from_component(comp: ComponentInfo, analysis: ScriptAnalysis) -> SlotDefinition:
    """Generate a slot definition from a component."""

    # Get swappable types
    allowed_types = get_swappable_types(comp.type)

    # Get category
    category = infer_category(comp)

    # Generate parameters from component params
    parameters = []
    for name, value in comp.params.items():
        if name.startswith("_"):  # Skip internal params
            continue
        if should_skip_parameter(name, value):
            continue
        if not isinstance(value, (int, float)):
            continue
        if isinstance(value, bool):
            continue

        # Determine range
        min_val = max(0.01, value * 0.2)
        max_val = value * 3
        step = value / 20

        # Adjust for specific parameter types
        if "angle" in name.lower():
            min_val, max_val, step = 1, 360, 1
        elif "layer" in name.lower():
            continue  # Skip layer params

        parameters.append(SlotParameter(
            name=name,
            label=name.replace("_", " ").title(),
            min_value=round(min_val, 3),
            max_value=round(max_val, 3),
            default_value=round(float(value), 3),
            step=round(step, 3) if step < 1 else round(step)
        ))

    # Generate display name
    display_name = comp.id.replace("_", " ").title()

    # Determine layer group
    layer_group = None
    if comp.layer:
        layer_group = f"Layer {comp.layer[0]}"

    return SlotDefinition(
        slot_id=comp.id,
        display_name=display_name,
        component_ids=[comp.id],
        current_type=comp.type,
        allowed_types=allowed_types,
        category=category,
        parameters=parameters,
        layer_group=layer_group
    )


def generate_layer_groups(components: List[ComponentInfo]) -> List[LayerGroup]:
    """Generate layer groups from component layers."""
    layer_slots: Dict[Tuple[int, int], List[str]] = {}

    for comp in components:
        if comp.layer:
            if comp.layer not in layer_slots:
                layer_slots[comp.layer] = []
            layer_slots[comp.layer].append(comp.id)

    # Default colors for layers
    layer_colors = [
        "#2E86AB",  # Blue
        "#F4A261",  # Orange
        "#E76F51",  # Red
        "#2A9D8F",  # Teal
        "#9B59B6",  # Purple
        "#3498DB",  # Light blue
    ]

    groups = []
    for i, (layer, slot_ids) in enumerate(sorted(layer_slots.items())):
        color = layer_colors[i % len(layer_colors)]
        groups.append(LayerGroup(
            name=f"Layer {layer[0]}",
            slot_ids=slot_ids,
            default_layer=layer,
            color=color
        ))

    # If no layers found, create a default group
    if not groups:
        all_slot_ids = [comp.id for comp in components]
        groups.append(LayerGroup(
            name="Default Layer",
            slot_ids=all_slot_ids,
            default_layer=(1, 0),
            color="#2E86AB"
        ))

    return groups


def find_global_parameters(analysis: ScriptAnalysis) -> List[GlobalParameter]:
    """
    Identify parameters that affect multiple components (global params).

    These are typically positional parameters like offsets that affect
    multiple component placements.
    """
    global_params = []
    seen: set[str] = set()

    # Module-level numeric assignments ARE the device's declared knobs under
    # the parametric contract ("tunables as top-level `name = value`") — the
    # live degrees of freedom the explorer exists to expose. Include them all.
    # Function params are included only when named like cross-cutting knobs.
    global_keywords = ["offset", "gap", "spacing", "margin", "padding"]

    for param in analysis.parameters:
        name_lower = param.name.lower()
        if param.context == "variable":
            is_global = True
        elif param.context == "function_param":
            is_global = any(kw in name_lower for kw in global_keywords)
        else:
            is_global = False

        if is_global and param.name not in seen:
            seen.add(param.name)
            min_val, max_val, step = param.suggested_range or (
                param.value * 0.2, param.value * 3, param.value / 20
            )

            global_params.append(GlobalParameter(
                name=param.name,
                label=param.name.replace("_", " ").title(),
                affects=[],  # Would need deeper analysis to determine
                min_value=round(min_val, 4),
                max_value=round(max_val, 4),
                # 4 decimals = 0.1 nm in um units; never round a knob's real
                # default into a different geometry.
                default_value=round(param.value, 4),
                step=round(step, 4) if step < 1 else round(step)
            ))

    return global_params


def generate_default_slots(analysis: ScriptAnalysis) -> SlotConfig:
    """
    Generate default slot configuration from script analysis.

    This provides full functionality without requiring the AI agent:
    - Each component becomes its own slot
    - Swappable types are auto-detected
    - Layer groups are inferred from existing layer assignments
    - Global parameters are identified by naming patterns

    Args:
        analysis: ScriptAnalysis from the analyzer

    Returns:
        SlotConfig with smart defaults
    """
    # Generate slots from components
    slots = []
    for comp in analysis.components:
        slot = generate_slot_from_component(comp, analysis)
        slots.append(slot)

    # If no components found from gf.components.*, try to create slots from parameters
    if not slots and analysis.parameters:
        # Create a single "device" slot with all parameters
        parameters = []
        for param in analysis.parameters:
            if param.context == "function_param" and not should_skip_parameter(param.name, param.value):
                min_val, max_val, step = param.suggested_range or (
                    param.value * 0.2, param.value * 3, param.value / 20
                )
                parameters.append(SlotParameter(
                    name=param.name,
                    label=param.name.replace("_", " ").title(),
                    min_value=round(min_val, 3),
                    max_value=round(max_val, 3),
                    default_value=round(param.value, 3),
                    step=round(step, 3) if step < 1 else round(step)
                ))

        if parameters:
            slots.append(SlotDefinition(
                slot_id="device",
                display_name="Device Parameters",
                component_ids=["device"],
                current_type="custom",
                allowed_types=["custom"],
                category="device",
                parameters=parameters,
                layer_group="Default Layer"
            ))

    # Always add tunable parameters from the main function as a device_params slot
    # This ensures slider ranges are available even when parameters aren't
    # attached to specific components
    main_func_params = []
    for param in analysis.parameters:
        # Look for parameters that are local variables in the main function
        if (param.parent_function == analysis.main_function and
            not should_skip_parameter(param.name, param.value) and
            isinstance(param.value, (int, float)) and
            not isinstance(param.value, bool)):

            min_val, max_val, step = param.suggested_range or (
                max(0.01, param.value * 0.2), param.value * 3, param.value / 20
            )
            main_func_params.append(SlotParameter(
                name=param.name,
                label=param.name.replace("_", " ").title(),
                min_value=round(min_val, 4),
                max_value=round(max_val, 4),
                default_value=round(param.value, 4),
                step=round(step, 4) if step < 1 else round(step)
            ))

    if main_func_params:
        slots.append(SlotDefinition(
            slot_id="device_params",
            display_name="Device Parameters",
            component_ids=["device_params"],
            current_type="parameters",
            allowed_types=["parameters"],
            category="parameters",
            parameters=main_func_params,
            layer_group=None
        ))

    # Generate layer groups
    layer_groups = generate_layer_groups(analysis.components)

    # Find global parameters
    global_params = find_global_parameters(analysis)

    return SlotConfig(
        slots=slots,
        layer_groups=layer_groups,
        global_params=global_params
    )
