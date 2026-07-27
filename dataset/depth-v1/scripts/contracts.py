"""Deterministic AST contracts for PixCell ``depth-v1`` realizations.

This module plans *realizations* of an already-approved representation.  It
does not invent representations, execute GDSFactory, render images, or admit
rows.  Its deliberately narrow responsibilities are:

* enumerate literal, module-level assignments in an accepted anchor program;
* classify which assignments are continuous realization axes;
* freeze context, topology, ports, pose, and implementation-only controls;
* group dimensions whose ordering or relationship should be preserved;
* emit the fixed ``r01``--``r07`` realization schedule; and
* rewrite only the right-hand side of explicitly named literal assignments.

The normalized grammar hash replaces selected assignment values by named
sentinels before hashing the AST.  ``rewrite_parameters`` additionally checks
the complete literal delta, so a matching hash cannot conceal an unrelated
assignment change.

The module is dependency-free and can be imported directly from its file path.
"""

from __future__ import annotations

import ast
import hashlib
import json
import math
import statistics
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any


SCHEDULE_VERSION = "depth-v1-r01-r07-v1"

# The schedule is intentionally explicit.  Fallback slots make a one- or
# two-axis grammar yield distinct realizations without changing a count or
# reaching into a function body for anonymous constants.
SCHEDULE = (
    ("r01", "primary", "low", 0.82),
    ("r02", "primary", "high", 1.18),
    ("r03", "secondary", "low", 0.84),
    ("r04", "secondary", "high", 1.16),
    ("r05", "tertiary", "low", 0.86),
    ("r06", "tertiary", "high", 1.14),
    ("r07", "interaction", "mixed", None),
)

SECONDARY_FALLBACK = {"low": 0.68, "high": 1.32}
TERTIARY_TO_SECONDARY_FALLBACK = {"low": 0.70, "high": 1.30}
TERTIARY_TO_PRIMARY_FALLBACK = {"low": 0.54, "high": 1.46}
INTERACTION_FACTORS = {"primary": 1.10, "secondary": 0.92, "tertiary": 1.08}


class ParameterClass(str, Enum):
    """Semantic class assigned to a module-level literal."""

    DIMENSION = "realization_dimension"
    ANGLE = "realization_angle"
    REPEAT_COUNT = "realization_repeat_count"
    CONTEXT = "frozen_context"
    TOPOLOGY = "frozen_topology"
    PORT = "frozen_port_contract"
    IMPLEMENTATION = "frozen_implementation"
    POSE = "frozen_pose"
    STRUCTURAL_LITERAL = "frozen_structural_literal"
    UNDECLARED = "frozen_undeclared_literal"


@dataclass(frozen=True)
class LiteralAssignment:
    """One simple, literal module-level assignment."""

    name: str
    value: Any
    literal_type: str
    line: int
    end_line: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ClassifiedParameter:
    """Classification and dependency membership for one literal."""

    name: str
    value: Any
    literal_type: str
    parameter_class: str
    mutable: bool
    reason: str
    dependency_key: str | None
    line: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ParameterAxis:
    """A dimension or ordered family that must be varied together."""

    axis_id: str
    names: tuple[str, ...]
    parameter_class: str
    priority: int
    dependency_kind: str

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["names"] = list(self.names)
        return value


@dataclass(frozen=True)
class ParameterContract:
    """JSON-serializable mutation contract for one approved anchor."""

    anchor_id: str
    grammar_id: str
    schedule_version: str
    source_grammar_hash: str
    assignments: tuple[ClassifiedParameter, ...]
    axes: tuple[ParameterAxis, ...]
    reference_scale_um: float
    declared_parameter_names: tuple[str, ...]

    @property
    def mutable_names(self) -> tuple[str, ...]:
        return tuple(
            parameter.name for parameter in self.assignments if parameter.mutable
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "anchor_id": self.anchor_id,
            "grammar_id": self.grammar_id,
            "schedule_version": self.schedule_version,
            "source_grammar_hash": self.source_grammar_hash,
            "reference_scale_um": self.reference_scale_um,
            "declared_parameter_names": list(self.declared_parameter_names),
            "mutable_names": list(self.mutable_names),
            "assignments": [item.to_dict() for item in self.assignments],
            "axes": [axis.to_dict() for axis in self.axes],
        }


@dataclass(frozen=True)
class CandidateSpec:
    """One deterministic descendant in the ``r01``--``r07`` schedule."""

    slot: str
    role: str
    direction: str
    updates: tuple[tuple[str, int | float], ...]
    axis_ids: tuple[str, ...]
    factors: tuple[tuple[str, float], ...]
    structural_count_deltas: tuple[tuple[str, int], ...]
    fallback: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "slot": self.slot,
            "role": self.role,
            "direction": self.direction,
            "updates": {name: value for name, value in self.updates},
            "axis_ids": list(self.axis_ids),
            "factors": {axis_id: factor for axis_id, factor in self.factors},
            "expected_structural_count_delta": {
                name: delta for name, delta in self.structural_count_deltas
            },
            "fallback": self.fallback,
        }


_PORT_NAMES = frozenset({"optical_port_specs", "port_names"})
_CONTEXT_NAMES = frozenset({"layer", "layers", "layer_spec", "cross_section"})
_IMPLEMENTATION_NAMES = frozenset(
    {
        "branch_cosine",
        "branch_sine",
        "control_fraction",
        "euler_fraction",
        "fanout_scale",
        "npoints",
        "transition_npoints",
        "transition_profile",
        "width_type",
    }
)
_IMPLEMENTATION_PARTS = (
    "attachment_overlap",
    "connection_overlap",
    "contact_overlap",
    "embedding",
    "edge_overlap",
    "minimum_bend_radius",
    "default_bend_radius",
    "minimum_spiral_radius",
)
_POSE_PARTS = ("global_rotation", "global_translation", "pose_")
_COUNT_EXACT = frozenset(
    {
        "columns",
        "count",
        "number_of_loops",
        "radial_count",
        "rows",
        "sides",
        "station_count",
    }
)
_PORTLESS_ARRAY_COUNT_GRAMMARS = frozenset(
    {
        "l2_17_composite_cell_2d_array__s01",
        "l2_17_composite_cell_2d_array__s02",
        "l2_17_composite_cell_2d_array__s03",
    }
)
_DEPENDENCY_QUALIFIERS = frozenset(
    {
        "bottom",
        "end",
        "far",
        "first",
        "inner",
        "input",
        "large",
        "left",
        "lower",
        "maximum",
        "minimum",
        "narrow",
        "near",
        "outer",
        "output",
        "primary",
        "right",
        "second",
        "secondary",
        "small",
        "start",
        "strong",
        "third",
        "top",
        "upper",
        "weak",
        "wide",
    }
)


def _is_scalar_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _literal_expression(value: Any) -> ast.expr:
    """Return an AST expression for a JSON-like Python literal."""

    try:
        expression = ast.parse(repr(value), mode="eval").body
        evaluated = ast.literal_eval(expression)
    except (SyntaxError, ValueError, TypeError) as exc:
        raise ValueError(f"update is not a supported literal: {value!r}") from exc
    if evaluated != value:
        raise ValueError(f"literal does not round-trip exactly: {value!r}")
    return expression


def top_level_literals(code: str) -> tuple[LiteralAssignment, ...]:
    """Enumerate simple literal assignments directly in ``Module.body``.

    Chained targets, destructuring, and computed right-hand sides are excluded
    rather than partially interpreted.
    """

    tree = ast.parse(code)
    found: list[LiteralAssignment] = []
    seen: set[str] = set()
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if len(targets) != 1 or not isinstance(targets[0], ast.Name):
            continue
        name = targets[0].id
        if name in seen:
            raise ValueError(f"duplicate module-level literal assignment: {name}")
        try:
            value = ast.literal_eval(node.value)
        except (ValueError, TypeError):
            continue
        seen.add(name)
        found.append(
            LiteralAssignment(
                name=name,
                value=value,
                literal_type=type(value).__name__,
                line=node.lineno,
                end_line=getattr(node, "end_lineno", node.lineno),
            )
        )
    return tuple(found)


def _declared_parameter_names(row: Mapping[str, Any] | None) -> tuple[str, ...]:
    if row is None:
        return ()
    raw = row.get("parameters_json")
    if raw is None:
        return ()
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError("parameters_json is not valid JSON") from exc
    elif isinstance(raw, Mapping):
        parsed = dict(raw)
    else:
        raise TypeError("parameters_json must be JSON text or a mapping")
    parameters = parsed.get("parameters", parsed)
    if not isinstance(parameters, Mapping):
        raise ValueError("parameters_json.parameters must be a mapping")
    return tuple(sorted(str(name) for name in parameters))


def _is_topology_name(name: str) -> bool:
    return (
        name in _COUNT_EXACT
        or name.startswith("n_")
        or name.endswith(("_count", "_counts", "_index", "_indices"))
        or "_count_" in name
        or "_per_" in name
        or name in {"channel_column", "defect_index", "peak_index"}
    )


def _dependency_key(name: str) -> tuple[str, str]:
    """Return a conservative relation key and its relation kind."""

    unit = ""
    stem = name
    for suffix in ("_um", "_deg"):
        if stem.endswith(suffix):
            stem = stem[: -len(suffix)]
            unit = suffix
            break
    tokens = stem.split("_")
    relation_kind = "independent"

    if tokens and tokens[-1] in {"x", "y"}:
        tokens[-1] = "axis"
        relation_kind = "coordinate_pair"

    reduced = [token for token in tokens if token not in _DEPENDENCY_QUALIFIERS]
    if len(reduced) != len(tokens):
        relation_kind = (
            "ordered_family" if relation_kind == "independent" else "ordered_axes"
        )
    if not reduced:
        reduced = tokens
    return "_".join(reduced) + unit, relation_kind


def _classify(
    assignment: LiteralAssignment,
    *,
    declared_names: set[str],
    declaration_required: bool,
    repeat_count_names: set[str],
) -> ClassifiedParameter:
    name = assignment.name
    value = assignment.value
    lowered = name.lower()

    if declaration_required and name not in declared_names and name not in _CONTEXT_NAMES:
        cls = ParameterClass.UNDECLARED
        reason = "not listed in parameters_json.parameters"
    elif name in _CONTEXT_NAMES or lowered.endswith("_layer"):
        cls = ParameterClass.CONTEXT
        reason = "material/layer context is invariant"
    elif name in _PORT_NAMES or "port_" in lowered or lowered.startswith("port"):
        cls = ParameterClass.PORT
        reason = "port identity or placement belongs to the frozen port contract"
    elif name in repeat_count_names:
        cls = ParameterClass.REPEAT_COUNT
        reason = "approved portless repeated-element count axis"
    elif isinstance(value, bool) or _is_topology_name(lowered):
        cls = ParameterClass.TOPOLOGY
        reason = "count, index, arity, or topology switch is invariant"
    elif name in _IMPLEMENTATION_NAMES or any(
        part in lowered for part in _IMPLEMENTATION_PARTS
    ):
        cls = ParameterClass.IMPLEMENTATION
        reason = "numerical resolution, continuity overlap, or routing tolerance"
    elif any(part in lowered for part in _POSE_PARTS):
        cls = ParameterClass.POSE
        reason = "pose is factored separately from a geometric realization"
    elif not _is_scalar_number(value):
        cls = ParameterClass.STRUCTURAL_LITERAL
        reason = "coordinate table, sequence, string, or other structural literal"
    elif lowered.endswith("_um"):
        cls = ParameterClass.DIMENSION
        reason = "declared continuous physical dimension"
    elif lowered.endswith("_deg"):
        cls = ParameterClass.ANGLE
        reason = "declared continuous internal angle"
    else:
        cls = ParameterClass.IMPLEMENTATION
        reason = "unitless or unclassified scalar is not an approved depth axis"

    mutable = cls in {
        ParameterClass.DIMENSION,
        ParameterClass.ANGLE,
        ParameterClass.REPEAT_COUNT,
    }
    dependency_key = _dependency_key(name)[0] if mutable else None
    return ClassifiedParameter(
        name=name,
        value=value,
        literal_type=assignment.literal_type,
        parameter_class=cls.value,
        mutable=mutable,
        reason=reason,
        dependency_key=dependency_key,
        line=assignment.line,
    )


def _axis_priority(names: Sequence[str]) -> int:
    """Rank axes by likely visible causal effect, then by stable name order."""

    joined = " ".join(names).lower()
    priorities = (
        ("gap", 120),
        ("pitch", 116),
        ("separation", 114),
        ("width", 110),
        ("radius", 106),
        ("length", 102),
        ("offset", 98),
        ("span", 96),
        ("height", 94),
        ("size", 92),
        ("step", 90),
        ("angle", 88),
        ("dx", 86),
        ("dy", 86),
        ("x_um", 84),
        ("y_um", 84),
    )
    score = 70
    for token, value in priorities:
        if token in joined:
            score = max(score, value)
    # A dependency family is slightly preferred because its covariance teaches
    # a real relationship while preserving the anchor's ordering.
    if len(names) > 1:
        score += 2
    return score


def _axes(parameters: Sequence[ClassifiedParameter]) -> tuple[ParameterAxis, ...]:
    groups: dict[tuple[str, str], list[ClassifiedParameter]] = {}
    for parameter in parameters:
        if not parameter.mutable or parameter.dependency_key is None:
            continue
        dependency_key, relation_kind = _dependency_key(parameter.name)
        groups.setdefault((dependency_key, relation_kind), []).append(parameter)

    axes: list[ParameterAxis] = []
    for (key, kind), members in groups.items():
        names = tuple(sorted(member.name for member in members))
        classes = {member.parameter_class for member in members}
        if classes == {ParameterClass.ANGLE.value}:
            parameter_class = ParameterClass.ANGLE.value
        elif classes == {ParameterClass.REPEAT_COUNT.value}:
            parameter_class = ParameterClass.REPEAT_COUNT.value
        else:
            parameter_class = ParameterClass.DIMENSION.value
        axis_id = f"axis:{key}" if len(names) > 1 else f"axis:{names[0]}"
        axes.append(
            ParameterAxis(
                axis_id=axis_id,
                names=names,
                parameter_class=parameter_class,
                priority=_axis_priority(names),
                dependency_kind=kind if len(names) > 1 else "independent",
            )
        )
    return tuple(sorted(axes, key=lambda axis: (-axis.priority, axis.axis_id)))


def _reference_scale(
    parameters: Sequence[ClassifiedParameter], row: Mapping[str, Any] | None
) -> float:
    candidates = [
        abs(float(parameter.value))
        for parameter in parameters
        if parameter.mutable
        and parameter.parameter_class == ParameterClass.DIMENSION.value
        and _is_scalar_number(parameter.value)
        and float(parameter.value) != 0.0
    ]
    if row is not None:
        footprint = row.get("footprint_um")
        if isinstance(footprint, Sequence) and not isinstance(footprint, (str, bytes)):
            candidates.extend(
                abs(float(value))
                for value in footprint
                if _is_scalar_number(value) and float(value) > 0
            )
    if not candidates:
        return 10.0
    # The median is insensitive to a long bus or a sub-micron waveguide and is
    # rounded solely to make the contract serialization stable.
    return round(float(statistics.median(candidates)), 8)


def classify_parameters(
    code: str, row: Mapping[str, Any] | None = None
) -> ParameterContract:
    """Build a deterministic contract from accepted anchor code and metadata."""

    if row is not None:
        role = row.get("variation_role")
        if role is not None and role != "semantic":
            raise ValueError(f"depth contracts require a semantic anchor, got {role!r}")
    declared = _declared_parameter_names(row)
    declared_set = set(declared)
    grammar_id = str(row.get("grammar_id", "")) if row is not None else ""
    repeat_count_names: set[str] = set()
    if grammar_id in _PORTLESS_ARRAY_COUNT_GRAMMARS:
        # These three approved grammars are portless repeated arrays.  Their
        # row/column counts are realization depth, not optical arity.
        repeat_count_names = {"rows", "columns"}
    assignments = tuple(
        _classify(
            assignment,
            declared_names=declared_set,
            declaration_required=bool(declared),
            repeat_count_names=repeat_count_names,
        )
        for assignment in top_level_literals(code)
    )
    anchor_id = str(row.get("id", "")) if row is not None else ""
    return ParameterContract(
        anchor_id=anchor_id,
        grammar_id=grammar_id,
        schedule_version=SCHEDULE_VERSION,
        source_grammar_hash=normalized_grammar_hash(code),
        assignments=assignments,
        axes=_axes(assignments),
        reference_scale_um=_reference_scale(assignments, row),
        declared_parameter_names=declared,
    )


def _rounded(value: float) -> float:
    result = round(float(value), 8)
    return 0.0 if result == -0.0 else result


def _scaled_value(
    value: int | float,
    factor: float,
    *,
    parameter_class: str,
    reference_scale_um: float,
) -> int | float:
    baseline = float(value)
    if parameter_class == ParameterClass.REPEAT_COUNT.value:
        delta = -1 if factor < 1.0 else 1
        return max(2, int(round(baseline)) + delta)
    if baseline != 0:
        return _rounded(baseline * factor)
    if parameter_class == ParameterClass.ANGLE.value:
        fallback_scale = 30.0
    else:
        fallback_scale = max(0.25, reference_scale_um * 0.10)
    return _rounded((factor - 1.0) * fallback_scale)


def _updates_for_axis(
    contract: ParameterContract, axis: ParameterAxis, factor: float
) -> dict[str, int | float]:
    assignments = {item.name: item for item in contract.assignments}
    return {
        name: _scaled_value(
            assignments[name].value,
            factor,
            parameter_class=assignments[name].parameter_class,
            reference_scale_um=contract.reference_scale_um,
        )
        for name in axis.names
    }


def _single_axis_spec(
    contract: ParameterContract,
    *,
    slot: str,
    role: str,
    direction: str,
    axis: ParameterAxis,
    factor: float,
    fallback: bool,
) -> CandidateSpec:
    updates = _updates_for_axis(contract, axis, factor)
    assignments = {item.name: item for item in contract.assignments}
    structural_deltas = tuple(
        sorted(
            (
                name,
                int(round(float(value) - float(assignments[name].value))),
            )
            for name, value in updates.items()
            if assignments[name].parameter_class == ParameterClass.REPEAT_COUNT.value
        )
    )
    return CandidateSpec(
        slot=slot,
        role=role,
        direction=direction,
        updates=tuple(sorted(updates.items())),
        axis_ids=(axis.axis_id,),
        factors=((axis.axis_id, factor),),
        structural_count_deltas=structural_deltas,
        fallback=fallback,
    )


def _multi_axis_spec(
    contract: ParameterContract,
    *,
    slot: str,
    role: str,
    direction: str,
    axis_factors: Sequence[tuple[ParameterAxis, float]],
    fallback: bool,
) -> CandidateSpec:
    assignments = {item.name: item for item in contract.assignments}
    updates: dict[str, int | float] = {}
    for axis, factor in axis_factors:
        updates.update(_updates_for_axis(contract, axis, factor))
    structural_deltas = tuple(
        sorted(
            (
                name,
                int(round(float(value) - float(assignments[name].value))),
            )
            for name, value in updates.items()
            if assignments[name].parameter_class == ParameterClass.REPEAT_COUNT.value
        )
    )
    return CandidateSpec(
        slot=slot,
        role=role,
        direction=direction,
        updates=tuple(sorted(updates.items())),
        axis_ids=tuple(axis.axis_id for axis, _ in axis_factors),
        factors=tuple((axis.axis_id, factor) for axis, factor in axis_factors),
        structural_count_deltas=structural_deltas,
        fallback=fallback,
    )


def candidate_specs(
    contract: ParameterContract, slot: str | None = None
) -> tuple[CandidateSpec, ...] | CandidateSpec:
    """Return the exact deterministic ``r01``--``r07`` mutation schedule.

    With no safe axes the result is an empty tuple.  If ``slot`` is provided,
    the matching spec is returned or ``KeyError`` is raised.
    """

    axes = contract.axes
    if not axes:
        if slot is not None:
            raise KeyError(f"{slot}: anchor has no safe realization axis")
        return ()

    primary = axes[0]
    secondary = axes[1] if len(axes) > 1 else None
    tertiary = axes[2] if len(axes) > 2 else None
    specs: list[CandidateSpec] = [
        _single_axis_spec(
            contract,
            slot="r01",
            role="primary",
            direction="low",
            axis=primary,
            factor=0.82,
            fallback=False,
        ),
        _single_axis_spec(
            contract,
            slot="r02",
            role="primary",
            direction="high",
            axis=primary,
            factor=1.18,
            fallback=False,
        ),
    ]

    if secondary is not None:
        secondary_axis = secondary
        secondary_factors = {"low": 0.84, "high": 1.16}
        secondary_fallback = False
    else:
        secondary_axis = primary
        secondary_factors = SECONDARY_FALLBACK
        secondary_fallback = True
    for slot_name, direction in (("r03", "low"), ("r04", "high")):
        specs.append(
            _single_axis_spec(
                contract,
                slot=slot_name,
                role="secondary",
                direction=direction,
                axis=secondary_axis,
                factor=secondary_factors[direction],
                fallback=secondary_fallback,
            )
        )

    repeat_pair = (
        len(axes) == 2
        and all(
            axis.parameter_class == ParameterClass.REPEAT_COUNT.value
            for axis in axes
        )
    )
    if repeat_pair:
        # A two-dimensional repeated array has no honest third scalar axis.
        # The tertiary fallback therefore changes both counts covariantly,
        # still by only one element per axis.
        for slot_name, direction, factor in (
            ("r05", "low", 0.86),
            ("r06", "high", 1.14),
        ):
            specs.append(
                _multi_axis_spec(
                    contract,
                    slot=slot_name,
                    role="tertiary",
                    direction=direction,
                    axis_factors=((primary, factor), (secondary, factor)),
                    fallback=True,
                )
            )
    elif tertiary is not None:
        tertiary_axis = tertiary
        tertiary_factors = {"low": 0.86, "high": 1.14}
        tertiary_fallback = False
    elif secondary is not None:
        tertiary_axis = secondary
        tertiary_factors = TERTIARY_TO_SECONDARY_FALLBACK
        tertiary_fallback = True
    else:
        tertiary_axis = primary
        tertiary_factors = TERTIARY_TO_PRIMARY_FALLBACK
        tertiary_fallback = True
    if not repeat_pair:
        for slot_name, direction in (("r05", "low"), ("r06", "high")):
            specs.append(
                _single_axis_spec(
                    contract,
                    slot=slot_name,
                    role="tertiary",
                    direction=direction,
                    axis=tertiary_axis,
                    factor=tertiary_factors[direction],
                    fallback=tertiary_fallback,
                )
            )

    interaction_axes = [primary]
    if secondary is not None:
        interaction_axes.append(secondary)
    if tertiary is not None:
        interaction_axes.append(tertiary)
    interaction_axis_factors: list[tuple[ParameterAxis, float]] = []
    for role, axis in zip(("primary", "secondary", "tertiary"), interaction_axes):
        interaction_axis_factors.append((axis, INTERACTION_FACTORS[role]))
    if repeat_pair:
        assignment_map = {item.name: item for item in contract.assignments}
        secondary_at_floor = all(
            int(assignment_map[name].value) <= 2 for name in secondary.names
        )
        if secondary_at_floor:
            interaction_axis_factors = ((primary, 0.90), (secondary, 1.08))
    specs.append(
        _multi_axis_spec(
            contract,
            slot="r07",
            role="interaction",
            direction="mixed",
            axis_factors=interaction_axis_factors,
            fallback=len(interaction_axes) < 3,
        )
    )

    result = tuple(specs)
    if len({item.slot for item in result}) != 7:
        raise AssertionError("internal schedule error: expected seven unique slots")
    if slot is None:
        return result
    for spec in result:
        if spec.slot == slot:
            return spec
    raise KeyError(f"unknown depth-v1 slot: {slot}")


class _NormalizeAssignments(ast.NodeTransformer):
    def __init__(self, names: set[str]) -> None:
        self.names = names

    def _normalize(
        self, node: ast.Assign | ast.AnnAssign
    ) -> ast.Assign | ast.AnnAssign:
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if len(targets) == 1 and isinstance(targets[0], ast.Name):
            name = targets[0].id
            if name in self.names:
                try:
                    ast.literal_eval(node.value)
                except (ValueError, TypeError):
                    return node
                node.value = ast.copy_location(
                    ast.Constant(value=f"__PIXCell_PARAMETER__:{name}"), node.value
                )
        return node

    def visit_Module(self, node: ast.Module) -> ast.Module:  # noqa: N802
        # Only direct children are eligible; assignments inside device() are
        # grammar, never mutable depth parameters.
        node.body = [
            self._normalize(child)
            if isinstance(child, (ast.Assign, ast.AnnAssign))
            else child
            for child in node.body
        ]
        return node


def normalized_grammar_hash(
    code: str, parameter_names: Iterable[str] | None = None
) -> str:
    """Hash an AST after replacing selected top-level literal RHS values.

    With no explicit names, every simple top-level literal is normalized.  Use
    ``prove_literal_rewrite`` when the exact allowed delta must be enforced.
    """

    if parameter_names is None:
        names = {assignment.name for assignment in top_level_literals(code)}
    else:
        names = set(parameter_names)
    tree = ast.parse(code)
    normalized = _NormalizeAssignments(names).visit(tree)
    ast.fix_missing_locations(normalized)
    payload = ast.dump(normalized, annotate_fields=True, include_attributes=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class _RewriteAssignments(ast.NodeTransformer):
    def __init__(self, updates: Mapping[str, Any]) -> None:
        self.updates = dict(updates)
        self.rewritten: set[str] = set()

    def _rewrite(self, node: ast.Assign | ast.AnnAssign) -> ast.AST:
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if len(targets) != 1 or not isinstance(targets[0], ast.Name):
            return node
        name = targets[0].id
        if name not in self.updates:
            return node
        try:
            old_value = ast.literal_eval(node.value)
        except (ValueError, TypeError) as exc:
            raise ValueError(f"{name} is not a literal assignment") from exc
        new_value = self.updates[name]
        if not _is_scalar_number(old_value) or not _is_scalar_number(new_value):
            raise TypeError(f"{name}: depth rewrites require scalar numeric literals")
        if not math.isfinite(float(new_value)):
            raise ValueError(f"{name}: update must be finite")
        node.value = ast.copy_location(_literal_expression(new_value), node.value)
        self.rewritten.add(name)
        return node

    def visit_Module(self, node: ast.Module) -> ast.Module:  # noqa: N802
        node.body = [
            self._rewrite(child)
            if isinstance(child, (ast.Assign, ast.AnnAssign))
            else child
            for child in node.body
        ]
        return node


def _literal_map(code: str) -> dict[str, Any]:
    return {assignment.name: assignment.value for assignment in top_level_literals(code)}


def prove_literal_rewrite(
    before: str, after: str, expected_updates: Mapping[str, int | float]
) -> dict[str, Any]:
    """Prove that exactly ``expected_updates`` changed and grammar was fixed."""

    expected = dict(expected_updates)
    before_literals = _literal_map(before)
    after_literals = _literal_map(after)
    if before_literals.keys() != after_literals.keys():
        raise AssertionError("module-level literal assignment set changed")
    unknown = sorted(set(expected) - before_literals.keys())
    if unknown:
        raise AssertionError(f"expected update names are absent: {unknown}")
    changed = {
        name
        for name in before_literals
        if before_literals[name] != after_literals[name]
    }
    expected_changed = {
        name
        for name, value in expected.items()
        if before_literals[name] != value
    }
    if changed != expected_changed:
        raise AssertionError(
            "literal delta mismatch: "
            f"observed={sorted(changed)} expected={sorted(expected_changed)}"
        )
    for name, value in expected.items():
        if after_literals[name] != value:
            raise AssertionError(
                f"{name}: observed {after_literals[name]!r}, expected {value!r}"
            )
    names = set(expected)
    before_hash = normalized_grammar_hash(before, names)
    after_hash = normalized_grammar_hash(after, names)
    if before_hash != after_hash:
        raise AssertionError("normalized AST grammar changed outside approved literals")
    return {
        "changed_names": sorted(changed),
        "frozen_literals_unchanged": True,
        "grammar_preserved": True,
        "normalized_grammar_hash": before_hash,
    }


def rewrite_parameters(code: str, updates: Mapping[str, int | float]) -> str:
    """Rewrite only named, literal module-level scalar assignments."""

    if not updates:
        raise ValueError("at least one parameter update is required")
    existing = _literal_map(code)
    missing = sorted(set(updates) - existing.keys())
    if missing:
        raise KeyError(f"unknown module-level literal assignments: {missing}")
    transformer = _RewriteAssignments(updates)
    tree = transformer.visit(ast.parse(code))
    if transformer.rewritten != set(updates):
        missing_rewrites = sorted(set(updates) - transformer.rewritten)
        raise AssertionError(f"failed to rewrite assignments: {missing_rewrites}")
    ast.fix_missing_locations(tree)
    rewritten = ast.unparse(tree) + "\n"
    prove_literal_rewrite(code, rewritten, updates)
    return rewritten


def contract_json(contract: ParameterContract) -> str:
    """Canonical JSON encoding used by manifests and deterministic tests."""

    return json.dumps(
        contract.to_dict(),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def audit_contracts(
    rows: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    """Classify and rewrite-test an iterable of semantic anchor rows."""

    anchors = 0
    schedulable = 0
    rewrite_proofs = 0
    effective_candidates = 0
    axis_histogram: dict[str, int] = {}
    class_histogram: dict[str, int] = {}
    unschedulable: list[dict[str, str]] = []
    no_effect_specs: list[dict[str, str]] = []
    duplicate_specs: list[dict[str, str]] = []
    for row in rows:
        if row.get("variation_role") != "semantic":
            continue
        anchors += 1
        contract = classify_parameters(str(row["code"]), row)
        axis_key = str(len(contract.axes))
        axis_histogram[axis_key] = axis_histogram.get(axis_key, 0) + 1
        for parameter in contract.assignments:
            class_histogram[parameter.parameter_class] = (
                class_histogram.get(parameter.parameter_class, 0) + 1
            )
        specs = candidate_specs(contract)
        if not specs:
            unschedulable.append(
                {
                    "id": str(row.get("id", "")),
                    "grammar_id": str(row.get("grammar_id", "")),
                    "reason": "no declared top-level continuous dimension or angle",
                }
            )
            continue
        schedulable += 1
        baseline = _literal_map(str(row["code"]))
        seen_effects: dict[tuple[tuple[str, int | float], ...], str] = {}
        for spec in specs:
            rewritten = rewrite_parameters(str(row["code"]), dict(spec.updates))
            proof = prove_literal_rewrite(
                str(row["code"]), rewritten, dict(spec.updates)
            )
            if not proof["grammar_preserved"]:
                raise AssertionError(f"{row.get('id')}/{spec.slot}: grammar changed")
            rewrite_proofs += 1
            effect = tuple(
                (name, value)
                for name, value in spec.updates
                if baseline[name] != value
            )
            if not effect:
                no_effect_specs.append(
                    {"id": str(row.get("id", "")), "slot": spec.slot}
                )
            elif effect in seen_effects:
                duplicate_specs.append(
                    {
                        "id": str(row.get("id", "")),
                        "slot": spec.slot,
                        "duplicates_slot": seen_effects[effect],
                    }
                )
            else:
                effective_candidates += 1
                seen_effects[effect] = spec.slot
    return {
        "schedule_version": SCHEDULE_VERSION,
        "semantic_anchors": anchors,
        "schedulable_anchors": schedulable,
        "unschedulable_anchors": unschedulable,
        "coverage": (schedulable / anchors) if anchors else 0.0,
        "rewrite_proofs": rewrite_proofs,
        "effective_candidates": effective_candidates,
        "no_effect_specs": no_effect_specs,
        "duplicate_specs": duplicate_specs,
        "axis_count_histogram": dict(
            sorted(axis_histogram.items(), key=lambda item: int(item[0]))
        ),
        "parameter_class_histogram": dict(sorted(class_histogram.items())),
    }


__all__ = [
    "CandidateSpec",
    "ClassifiedParameter",
    "LiteralAssignment",
    "ParameterAxis",
    "ParameterClass",
    "ParameterContract",
    "SCHEDULE",
    "SCHEDULE_VERSION",
    "audit_contracts",
    "candidate_specs",
    "classify_parameters",
    "contract_json",
    "normalized_grammar_hash",
    "prove_literal_rewrite",
    "rewrite_parameters",
    "top_level_literals",
]
