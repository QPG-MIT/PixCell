"""
Weber Integration Module for HOMI

Provides Weber's interactive explorer functionality embedded in the main app.
This module uses Weber's full analyzer and slot generation for complete functionality.
"""

import ast
import math
from typing import List, Dict, Any, Optional, Tuple

import gdsfactory as gf

# Import Weber's full analyzer and slot generation by absolute package name.
# (Weber's core used to be reached as a top-level ``core`` via sys.path insertion,
# which clashed with jee/core; fixed structurally by the src/ package layout.)
from weber.core.analyzer import (
    analyze_script_from_source,
    ScriptAnalysis,
    ParameterInfo,
    ComponentInfo,
)
from weber.core.default_slots import (
    generate_default_slots,
    SlotConfig,
    SlotDefinition,
    SlotParameter,
    LayerGroup,
    GlobalParameter,
)
from weber.core.config import should_skip_parameter, suggest_slider_range


# =============================================================================
# LAYER HANDLING UTILITIES
# =============================================================================

def has_boolean_operations(script_source: str) -> bool:
    """
    Check if script uses boolean operations that merge geometry.

    Scripts with boolean operations cannot support per-slot layer assignment
    because the geometry is merged into a single layer.

    Args:
        script_source: Python source code of the GDSFactory script

    Returns:
        True if script contains boolean/flatten operations
    """
    import re
    patterns = [
        r'gf\.boolean\s*\(',       # gf.boolean(...)
        r'\.boolean\s*\(',          # component.boolean(...)
        r'\.flatten\s*\(\s*\)',     # component.flatten()
    ]
    return any(re.search(p, script_source) for p in patterns)


def apply_global_layer_override(script_source: str, layer_override: Tuple[int, int]) -> str:
    """
    Apply a single global layer override to all layer assignments in the script.

    Handles common patterns:
    - layer = (1, 0)
    - layer_wg = (1, 0)
    - LAYER = (1, 0)
    - layer: tuple = (1, 0)

    Args:
        script_source: Python source code
        layer_override: Tuple (layer, datatype) to replace all layer assignments

    Returns:
        Modified source code with layers replaced
    """
    import re
    layer_str = f"({layer_override[0]}, {layer_override[1]})"

    # Pattern 1: Variable assignments (layer, layer_wg, LAYER, layer_core, etc.)
    # Preserves the variable name, replaces only the tuple value
    script_source = re.sub(
        r'((?:layer|LAYER)(?:_\w*)?)\s*=\s*\(\s*\d+\s*,\s*\d+\s*\)',
        rf'\1 = {layer_str}',
        script_source,
        flags=re.IGNORECASE
    )

    # Pattern 2: Type-annotated function parameters
    # Matches: layer: tuple = (1, 0), layer: LayerSpec = (1, 0)
    script_source = re.sub(
        r'(layer\s*:\s*\w+\s*=\s*)\(\s*\d+\s*,\s*\d+\s*\)',
        rf'\1{layer_str}',
        script_source,
        flags=re.IGNORECASE
    )

    return script_source


def apply_per_slot_layers(
    script_source: str,
    analysis: 'ScriptAnalysis',
    component_map: Dict[str, List[str]],
    layer_assignments: Dict[str, Tuple[int, int]]
) -> str:
    """
    Replace layer= argument in each component call based on slot assignment.

    This enables per-slot layer assignment for scripts without boolean operations.

    Args:
        script_source: Python source code
        analysis: ScriptAnalysis with component info including line numbers
        component_map: Dict mapping slot_id to list of component_ids
        layer_assignments: Dict mapping slot_id to (layer, datatype) tuple

    Returns:
        Modified source code with per-component layers
    """
    import re

    # Build reverse map: component_id -> slot_id
    comp_to_slot = {}
    for slot_id, comp_ids in component_map.items():
        for comp_id in comp_ids:
            comp_to_slot[comp_id] = slot_id

    # Sort components by line number (descending) to replace from bottom up
    # This prevents line number shifts from affecting later replacements
    components = sorted(analysis.components, key=lambda c: c.line_number, reverse=True)

    lines = script_source.split('\n')

    for comp in components:
        slot_id = comp_to_slot.get(comp.id)
        if not slot_id:
            continue

        layer = layer_assignments.get(slot_id, (1, 0))
        layer_str = f"({layer[0]}, {layer[1]})"

        # Replace layer= argument on the component's line
        line_idx = comp.line_number - 1  # 0-indexed
        if 0 <= line_idx < len(lines):
            # Pattern: layer=(x, y) or layer = (x, y)
            lines[line_idx] = re.sub(
                r'layer\s*=\s*\(\s*\d+\s*,\s*\d+\s*\)',
                f'layer={layer_str}',
                lines[line_idx]
            )

    return '\n'.join(lines)


from contextlib import contextmanager  # noqa: E402


@contextmanager
def layer_call_interceptor(
    analysis: 'ScriptAnalysis',
    component_map: Dict[str, List[str]],
    layer_assignments: Dict[str, Tuple[int, int]],
):
    """Per-slot layer assignment for CONTRACT scripts, at runtime.

    Contract scripts pass ``layer=layer`` (a shared variable) across
    multi-line calls, so source rewriting (``apply_per_slot_layers``) cannot
    retarget them. Instead: while the context is active, the gf.components
    factories the script uses are wrapped; each invocation looks up the
    CALLER'S LINE NUMBER (the call site the analyzer recorded) and overrides
    the ``layer`` kwarg with the slot's assignment. Loop-safe (a call site
    executed N times retargets all N instances) and multi-line-safe.

    Geometry is layer-invariant: assignments never change shapes, only which
    GDS layer carries them.
    """
    import sys as _sys

    comp_to_slot: Dict[str, str] = {}
    for slot_id, comp_ids in component_map.items():
        for comp_id in comp_ids:
            comp_to_slot[comp_id] = slot_id

    line_to_layer: Dict[int, Tuple[int, int]] = {}
    factory_names = set()
    for comp in analysis.components:
        slot_id = comp_to_slot.get(comp.id)
        if not slot_id:
            continue
        assigned = layer_assignments.get(slot_id)
        if assigned and tuple(assigned) != (1, 0):
            line_to_layer[comp.line_number] = tuple(assigned)
        factory_names.add(comp.type)

    if not line_to_layer:
        yield
        return

    originals = {}
    try:
        for name in factory_names:
            orig = getattr(gf.components, name, None)
            if orig is None:
                continue
            originals[name] = orig

            def _wrap(_orig):
                def _inner(*args, **kwargs):
                    assigned = line_to_layer.get(_sys._getframe(1).f_lineno)
                    if assigned is not None:
                        kwargs["layer"] = assigned
                    return _orig(*args, **kwargs)
                return _inner

            setattr(gf.components, name, _wrap(orig))
        yield
    finally:
        for name, orig in originals.items():
            setattr(gf.components, name, orig)


# =============================================================================
# DEVICE BUILDER
# =============================================================================

def build_device_with_params(
    script_source: str,
    slider_values: Dict[str, float],
    main_function: Optional[str] = None,
    component_swaps: Optional[Dict[str, str]] = None,
    layer_override: Optional[Tuple[int, int]] = None,
    # Per-slot layer support (for scripts without boolean operations)
    analysis: Optional['ScriptAnalysis'] = None,
    component_map: Optional[Dict[str, List[str]]] = None,
    layer_assignments: Optional[Dict[str, Tuple[int, int]]] = None
) -> gf.Component:
    """
    Build a GDSFactory component by executing the script with injected parameters.

    Supports two layer assignment modes:
    - **Complex scripts (with boolean/flatten):** Single global layer via layer_override
    - **Simple scripts (no boolean):** Per-slot layers via analysis + component_map + layer_assignments

    Args:
        script_source: Python source code of the GDSFactory script
        slider_values: Dict mapping parameter name to slider value
        main_function: Name of the main function to call (auto-detected if None)
        component_swaps: Dict mapping original component type to new type
                        e.g., {"bend_circular": "bend_euler"}
        layer_override: Optional tuple (layer, datatype) for global layer replacement
        analysis: ScriptAnalysis for per-slot layer support
        component_map: Dict mapping slot_id to list of component_ids
        layer_assignments: Dict mapping slot_id to (layer, datatype) tuple

    Returns:
        GDSFactory Component

    Raises:
        RuntimeError: If component cannot be built
    """
    import re

    # Clear GDSFactory cache to ensure fresh component
    gf.clear_cache()

    # Modify script source to inject slider values
    # Replace variable assignments like "var_name = 0.5" with new values
    modified_source = script_source
    for name, value in slider_values.items():
        # Pattern matches: variable_name = number (with optional comment)
        # Handles int, float, negative numbers
        pattern = rf'(\b{re.escape(name)}\s*=\s*)(-?\d+\.?\d*)'
        replacement = rf'\g<1>{value}'
        modified_source = re.sub(pattern, replacement, modified_source)

    # Apply component swaps if provided
    if component_swaps:
        for old_type, new_type in component_swaps.items():
            if old_type != new_type:
                # Replace gf.components.old_type with gf.components.new_type
                pattern = rf'gf\.components\.{re.escape(old_type)}\b'
                modified_source = re.sub(pattern, f'gf.components.{new_type}', modified_source)

    # Layer handling: choose path based on script complexity
    is_complex = has_boolean_operations(modified_source)

    if is_complex:
        # Path A: Complex script (boolean/flatten) - use single global layer
        if layer_override:
            modified_source = apply_global_layer_override(modified_source, layer_override)
        elif layer_assignments:
            # Use first layer assignment as global override for complex scripts
            first_layer = next(iter(layer_assignments.values()), None)
            if first_layer:
                modified_source = apply_global_layer_override(modified_source, first_layer)
    else:
        # Path B: Simple script - try per-slot layers first
        if analysis and component_map and layer_assignments:
            modified_source = apply_per_slot_layers(
                modified_source, analysis, component_map, layer_assignments
            )
            # Also apply global override for any remaining layer= patterns
            # (e.g., in cross_sections that aren't tied to specific components)
            first_layer = next(iter(layer_assignments.values()), None)
            if first_layer:
                modified_source = apply_global_layer_override(modified_source, first_layer)
        elif layer_override:
            # Fallback to global override if per-slot info not provided
            modified_source = apply_global_layer_override(modified_source, layer_override)

    # Create namespace with gdsfactory
    namespace = {
        'gf': gf,
        'gdsfactory': gf,
        '__name__': '__weber_embedded__',
    }

    # Also inject slider values into namespace (for scripts that use globals)
    for name, value in slider_values.items():
        namespace[name] = value

    # Execute the modified script
    exec(modified_source, namespace)

    # Try to find and call the main function
    if main_function and main_function in namespace:
        result = namespace[main_function]
        if callable(result):
            return result()
        return result

    # Fallback: look for any @gf.cell decorated function
    for key, val in namespace.items():
        if callable(val) and hasattr(val, '_cell_name'):
            return val()

    # Fallback: look for Component instance
    for key, val in namespace.items():
        if isinstance(val, gf.Component):
            return val

    raise RuntimeError("Could not build component from script")


def get_default_slider_values(slot_config: SlotConfig) -> Dict[str, float]:
    """
    Get default slider values from slot configuration.

    Args:
        slot_config: SlotConfig with slot definitions

    Returns:
        Dict mapping parameter name to default value
    """
    values = {}
    for slot in slot_config.slots:
        for param in slot.parameters:
            values[param.name] = param.default_value
    return values


# =============================================================================
# HIGH-LEVEL API
# =============================================================================

def analyze_and_configure(script_source: str) -> Tuple[ScriptAnalysis, SlotConfig]:
    """
    Analyze a GDSFactory script and generate configuration using Weber's full analyzer.

    This uses Weber's complete analysis which includes:
    - Multiple slots per device (not just device_params)
    - Component detection with allowed_types for swapping
    - Per-component layer assignment support
    - Category-based organization

    Args:
        script_source: Python source code

    Returns:
        Tuple of (ScriptAnalysis, SlotConfig)
    """
    # Use Weber's full analyzer
    analysis = analyze_script_from_source(script_source, name="<homi_generated>")

    # Use Weber's full slot generation with smart defaults
    config = generate_default_slots(analysis)

    return analysis, config


def get_parameter_info_for_ui(slot_config: SlotConfig) -> List[Dict[str, Any]]:
    """
    Get parameter information formatted for UI rendering.

    Args:
        slot_config: SlotConfig with slot definitions

    Returns:
        List of dicts with parameter info for sliders
    """
    params = []
    seen = set()
    for slot in slot_config.slots:
        for param in slot.parameters:
            seen.add(param.name)
            params.append({
                "name": param.name,
                "label": param.label,
                "min_value": param.min_value,
                "max_value": param.max_value,
                "default_value": param.default_value,
                "step": param.step,
                "unit": param.unit,
                "slot_id": slot.slot_id,
                "category": slot.category,
            })
    # Top-level tunables (the parametric contract's knob shape) live in
    # global_params, not in any slot — without these, contract-shaped scripts
    # report ZERO tunables to every consumer (marimo workbench, MCP parameter
    # suggestions, the JEE optimizer).
    for gp in getattr(slot_config, "global_params", []) or []:
        if gp.name in seen:
            continue
        seen.add(gp.name)
        params.append({
            "name": gp.name,
            "label": gp.label,
            "min_value": gp.min_value,
            "max_value": gp.max_value,
            "default_value": gp.default_value,
            "step": gp.step,
            "unit": "um",
            "slot_id": None,
            "category": "global",
        })
    return params


def _is_int_annotation(annotation: ast.expr | None) -> bool:
    """Return whether an annotation explicitly declares integer semantics.

    A bare numeric literal is not enough: ``length = 10`` is commonly a
    continuous micron-valued dimension.  The explicit ``: int`` contract is
    what identifies counts that must remain integral during a rebuild.
    """
    if annotation is None:
        return False
    try:
        text = ast.unparse(annotation).replace(" ", "")
    except Exception:
        return False
    return text in {"int", "builtins.int"} or text.startswith("Annotated[int,")


def _explicit_integer_parameters(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if (isinstance(node, ast.AnnAssign)
                and isinstance(node.target, ast.Name)
                and _is_int_annotation(node.annotation)):
            names.add(node.target.id)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for arg in (*node.args.posonlyargs, *node.args.args,
                        *node.args.kwonlyargs):
                if _is_int_annotation(arg.annotation):
                    names.add(arg.arg)
    return names


def _parameter_unit(param: Dict[str, Any], *, name: str,
                    value_type: str) -> str:
    """Preserve Weber units, correcting its generic fallback when evident."""
    raw = str(param.get("unit") or "").strip()
    if raw and raw not in {"um", "µm", "μm"}:
        return raw
    lower = name.lower()
    if "angle" in lower or lower.endswith("_deg"):
        return "°"
    count_words = ("count", "num_", "number", "slices", "segments",
                   "points", "teeth", "periods")
    if value_type == "integer" and any(word in lower for word in count_words):
        return "count"
    return "µm"


def get_live_parameter_info(script_source: str) -> List[Dict[str, Any]]:
    """Return the canonical live-knob schema shared by every workbench.

    Weber owns parameter discovery and suggested ranges.  This final pass
    applies the generated Marimo workbench's anti-deception rule: a parameter
    is exposed only when the program actually reads it.  AST loads are used
    instead of textual occurrence counts so comments and strings cannot make a
    dead constant look live.  Explicit integer annotations are preserved so a
    UI or optimizer never substitutes ``26.4`` into ``range(slices)``.
    """
    tree = ast.parse(script_source)
    loaded = {
        node.id for node in ast.walk(tree)
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
    }
    int_names = _explicit_integer_parameters(tree)
    analysis, slot_config = analyze_and_configure(script_source)
    params = get_parameter_info_for_ui(slot_config)
    eligible = {p.name for p in analysis.get_tunable_parameters()}

    live: List[Dict[str, Any]] = []
    for original in params:
        name = str(original.get("name") or "")
        default = original.get("default_value")
        if (not name or name.startswith("_") or name not in eligible
                or name not in loaded
                or should_skip_parameter(name, default)
                or not isinstance(default, (int, float))
                or isinstance(default, bool)):
            continue

        param = dict(original)
        value_type = "integer" if name in int_names else "float"
        if value_type == "integer":
            value = int(round(float(default)))
            lo = int(math.ceil(float(param["min_value"])))
            hi = int(math.floor(float(param["max_value"])))
            param["default_value"] = value
            param["min_value"] = min(lo, value)
            param["max_value"] = max(hi, value)
            param["step"] = max(1, int(round(float(param.get("step") or 1))))
        else:
            param["default_value"] = float(default)
            param["min_value"] = float(param["min_value"])
            param["max_value"] = float(param["max_value"])
            param["step"] = float(param["step"])
        param["value_type"] = value_type
        param["unit"] = _parameter_unit(param, name=name,
                                         value_type=value_type)
        live.append(param)
    return live


def build_component_map(slot_config: SlotConfig) -> Dict[str, List[str]]:
    """
    Build a component map from slot configuration.

    Args:
        slot_config: SlotConfig with slot definitions

    Returns:
        Dict mapping slot_id to list of component_ids
    """
    return {slot.slot_id: slot.component_ids for slot in slot_config.slots}


def build_device_slots_dict(slot_config: SlotConfig) -> Dict[str, Dict[str, Any]]:
    """
    Build device slots dictionary for layer assignment UI.

    Args:
        slot_config: SlotConfig with slot definitions

    Returns:
        Dict compatible with Weber's render_layer_assignments()
    """
    device_slots = {}
    for slot in slot_config.slots:
        device_slots[slot.slot_id] = {
            "display_name": slot.display_name,
            "component_ids": slot.component_ids,
            "original_type": slot.current_type,  # Store original for swap detection
            "current_type": slot.current_type,
            "allowed_types": slot.allowed_types,
            "category": slot.category,
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
                for p in slot.parameters
            ],
            "layer_group": slot.layer_group,
        }
    return device_slots


# Re-export for convenience
__all__ = [
    # Analysis
    'analyze_and_configure',
    'analyze_script_from_source',
    'ScriptAnalysis',
    'ParameterInfo',
    'ComponentInfo',

    # Slot configuration
    'SlotConfig',
    'SlotDefinition',
    'SlotParameter',
    'LayerGroup',
    'GlobalParameter',
    'generate_default_slots',

    # Device building
    'build_device_with_params',
    'get_default_slider_values',

    # Layer handling
    'has_boolean_operations',
    'apply_global_layer_override',
    'apply_per_slot_layers',

    # UI helpers
    'get_parameter_info_for_ui',
    'get_live_parameter_info',
    'build_component_map',
    'build_device_slots_dict',

    # Config helpers
    'should_skip_parameter',
    'suggest_slider_range',
]
