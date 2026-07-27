"""Deterministic execution and raster gates for PixCell depth-v1.

This module intentionally lives below ``dataset/depth-v1``.  It does not
modify or participate in the frozen core-v1 build.  Its inputs are programs
that have already passed the PixCell source/purity gate; the additional source
checks here make the runtime boundary narrow, but are not a replacement for
that gate.

The public entry points are:

``execute_program``
    Execute a program in a short-lived subprocess and return flattened
    polygons, ports, a bounding box, and structural witnesses.
``render_geometry``
    Produce either a square maximum-visibility view or an isotropically scaled
    physical-aspect view as deterministic black-on-white PNG bytes.
``compare_geometry_masks``
    Rasterize two executions into one shared coordinate frame and compute IoU
    and symmetric mask delta.  A shared frame is load-bearing: independently
    fitted images would hide footprint changes.
``gate_ports``
    Check terminal count, orientation/edge-side signature, unique names, and
    material immediately inside every declared terminal.

The subprocess is a containment boundary for accidental hangs and module-level
state.  It is not a general untrusted-code sandbox.  Callers must run the
strict PixCell source/purity gate before this module.
"""

from __future__ import annotations

import argparse
import ast
import io
import json
import math
import os
import subprocess
import sys
import tempfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
from PIL import Image, ImageChops, ImageDraw
from shapely import make_valid
from shapely.geometry import (
    GeometryCollection,
    LineString,
    MultiLineString,
    MultiPolygon,
    Polygon,
)
from shapely.ops import unary_union


ALLOWED_IMPORTS = frozenset(
    {"gdsfactory", "json", "math", "numpy", "pathlib"}
)
FORBIDDEN_CALL_NAMES = frozenset(
    {
        "__import__",
        "breakpoint",
        "compile",
        "eval",
        "exec",
        "input",
        "open",
    }
)
FORBIDDEN_ATTRIBUTE_ROOTS = frozenset(
    {
        "asyncio",
        "builtins",
        "http",
        "os",
        "requests",
        "shutil",
        "socket",
        "subprocess",
        "sys",
        "urllib",
    }
)
CARDINAL_ANGLES = (0.0, 90.0, 180.0, 270.0)
DEFAULT_TIMEOUT_SECONDS = 60.0
MAX_STDERR_CHARS = 4_000
COORDINATE_DECIMALS = 6
# The pinned 1 nm database grid makes this 10 square DBU. Core-v1 has a
# >31,000x area gap between sub-resolution polygonization debris and its
# smallest intentional material hole.
MIN_VISIBLE_HOLE_AREA_UM2 = 1e-5


class RuntimeGateError(RuntimeError):
    """Raised when execution or a deterministic gate fails."""


@dataclass(frozen=True)
class RenderedPNG:
    """A raster plus the world-to-pixel transform used to create it."""

    png_bytes: bytes
    mode: str
    canvas_px: tuple[int, int]
    world_bounds_um: tuple[float, float, float, float]
    scale_px_per_um: tuple[float, float]
    margin_px: int


@dataclass(frozen=True)
class MaskDelta:
    """Pixel comparison in a shared coordinate frame."""

    iou: float
    changed_fraction: float
    xor_pixels: int
    union_pixels: int
    reference_pixels: int
    candidate_pixels: int


@dataclass(frozen=True)
class PortWitness:
    """Observed relationship between one port and the rendered material."""

    name: str
    side: str
    bbox_side: str | None
    orientation_deg: float
    width_um: float
    inward_material_fraction: float
    outward_material_fraction: float
    touches_material: bool


@dataclass(frozen=True)
class PortGateReport:
    """Deterministic port gate result."""

    passed: bool
    errors: tuple[str, ...]
    port_count: int
    orientation_side_histogram: dict[str, int]
    witnesses: tuple[PortWitness, ...]


@dataclass(frozen=True)
class CandidateGateReport:
    """Combined representation-preservation witnesses for one realization."""

    passed: bool
    errors: tuple[str, ...]
    port_gate: PortGateReport
    structural_deltas: dict[str, tuple[Any, Any]]
    mask_delta: MaskDelta


def _round_float(value: float) -> float:
    rounded = round(float(value), COORDINATE_DECIMALS)
    return 0.0 if rounded == -0.0 else rounded


def _dotted_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _dotted_name(node.value)
        return f"{base}.{node.attr}" if base else None
    return None


def _is_main_guard(node: ast.If) -> bool:
    test = node.test
    if not isinstance(test, ast.Compare) or len(test.ops) != 1:
        return False
    if not isinstance(test.ops[0], ast.Eq) or len(test.comparators) != 1:
        return False
    pairs = ((test.left, test.comparators[0]), (test.comparators[0], test.left))
    return any(
        isinstance(left, ast.Name)
        and left.id == "__name__"
        and isinstance(right, ast.Constant)
        and right.value == "__main__"
        for left, right in pairs
    )


def sanitize_source(source: str) -> str:
    """Return an executable module with its standalone writer removed.

    Depth-v1 consumes programs that have already passed the strict public
    source/purity gate.  This second check deliberately admits only the module
    shape used by the frozen core: imports, literal parameters, function/class
    definitions, and an optional ``if __name__ == "__main__"`` writer.
    """

    try:
        tree = ast.parse(source, filename="<pixcell-depth-source>")
    except SyntaxError as exc:
        raise RuntimeGateError(f"source does not compile: {exc}") from exc

    retained: list[ast.stmt] = []
    for node in tree.body:
        if isinstance(node, ast.If) and _is_main_guard(node):
            continue
        if not isinstance(
            node,
            (ast.Import, ast.ImportFrom, ast.Assign, ast.AnnAssign, ast.FunctionDef,
             ast.AsyncFunctionDef, ast.ClassDef),
        ):
            raise RuntimeGateError(
                "unsupported executable top-level statement: "
                f"{type(node).__name__}"
            )
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            try:
                ast.literal_eval(node.value)
            except (TypeError, ValueError) as exc:
                raise RuntimeGateError(
                    "top-level parameters must be literal assignments"
                ) from exc
        retained.append(node)
    tree.body = retained
    ast.fix_missing_locations(tree)

    for node in ast.walk(tree):
        modules: list[str] = []
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                raise RuntimeGateError("relative imports are not allowed")
            modules.append(node.module or "")
        for module in modules:
            root = module.split(".", 1)[0]
            if root not in ALLOWED_IMPORTS:
                raise RuntimeGateError(f"runtime import is not allowed: {module}")
        if not isinstance(node, ast.Call):
            continue
        dotted = _dotted_name(node.func)
        if isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_CALL_NAMES:
            raise RuntimeGateError(f"runtime call is not allowed: {node.func.id}")
        if dotted and dotted.split(".", 1)[0] in FORBIDDEN_ATTRIBUTE_ROOTS:
            raise RuntimeGateError(f"runtime call is not allowed: {dotted}")

    device_functions = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == "device"
    ]
    if len(device_functions) != 1 or isinstance(
        device_functions[0], ast.AsyncFunctionDef
    ):
        raise RuntimeGateError("source must define exactly one synchronous device()")
    return ast.unparse(tree) + "\n"


def source_structural_metrics(source: str) -> dict[str, Any]:
    """Extract stable AST witnesses without assigning semantic meaning."""

    tree = ast.parse(source)
    primitive_calls: Counter[str] = Counter()
    reference_operations: Counter[str] = Counter()
    loop_count = 0
    conditional_count = 0
    for node in ast.walk(tree):
        if isinstance(node, (ast.For, ast.While)):
            loop_count += 1
        elif isinstance(node, ast.If):
            conditional_count += 1
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.LShift):
            reference_operations["lshift"] += 1
        if not isinstance(node, ast.Call):
            continue
        dotted = _dotted_name(node.func)
        if not dotted:
            continue
        if ".components." in dotted:
            primitive_calls[dotted.rsplit(".", 1)[-1]] += 1
        elif ".path." in dotted:
            primitive_calls[f"path.{dotted.rsplit('.', 1)[-1]}"] += 1
        elif dotted.endswith(".extrude_transition"):
            primitive_calls["extrude_transition"] += 1
        elif dotted.endswith(".extrude"):
            primitive_calls["extrude"] += 1
        elif dotted.endswith(".boolean"):
            primitive_calls["boolean"] += 1
        leaf = dotted.rsplit(".", 1)[-1]
        if leaf in {"add", "add_ref", "add_refs", "create_inst"}:
            reference_operations[leaf] += 1
    return {
        "conditional_count": conditional_count,
        "loop_count": loop_count,
        "primitive_call_count": sum(primitive_calls.values()),
        "primitive_call_histogram": dict(sorted(primitive_calls.items())),
        "reference_operation_count": sum(reference_operations.values()),
        "reference_operation_histogram": dict(
            sorted(reference_operations.items())
        ),
    }


def _polygon_points(polygon: Any, dbu: float) -> dict[str, Any]:
    converted = polygon.to_dtype(dbu)
    exterior = [
        [_round_float(point.x), _round_float(point.y)]
        for point in converted.each_point_hull()
    ]
    holes = [
        [
            [_round_float(point.x), _round_float(point.y)]
            for point in converted.each_point_hole(index)
        ]
        for index in range(converted.holes())
    ]
    if len(exterior) < 3:
        raise RuntimeGateError("execution emitted a degenerate polygon")
    return {"exterior": exterior, "holes": holes}


def _runtime_record(source: str) -> dict[str, Any]:
    """Execute sanitized source inside the worker process."""

    import gdsfactory as gf

    namespace: dict[str, Any] = {
        "__builtins__": __builtins__,
        "__file__": "<pixcell-depth-program>",
        "__name__": "pixcell_depth_program",
        "__package__": None,
    }
    gf.clear_cache()
    compiled = compile(source, "<pixcell-depth-program>", "exec")
    exec(compiled, namespace, namespace)
    device = namespace.get("device")
    if not callable(device):
        raise RuntimeGateError("program did not define callable device()")
    component = device()

    dbu = float(component.kcl.dbu)
    polygons: list[dict[str, Any]] = []
    raw_polygons = component.get_polygons(by="tuple")
    for layer, layer_polygons in sorted(raw_polygons.items()):
        for polygon in layer_polygons:
            record = _polygon_points(polygon, dbu)
            record["layer"] = [int(layer[0]), int(layer[1])]
            polygons.append(record)
    if not polygons:
        raise RuntimeGateError("execution emitted no material polygons")

    ports = [
        {
            "center": [_round_float(value) for value in port.dcenter],
            "name": str(port.name),
            "orientation": _round_float(float(port.orientation) % 360.0),
            "port_type": str(port.port_type),
            "width": _round_float(port.dwidth),
        }
        for port in component.ports
    ]
    geometry = _geometry_from_polygons(polygons)
    min_x, min_y, max_x, max_y = map(float, geometry.bounds)
    bbox = np.asarray([[min_x, min_y], [max_x, max_y]], dtype=float)
    if bbox.shape != (2, 2) or not np.isfinite(bbox).all():
        raise RuntimeGateError(f"unexpected material bbox: {bbox!r}")
    span = bbox[1] - bbox[0]
    if np.any(span <= 0):
        raise RuntimeGateError(f"non-positive material span: {span!r}")
    geometry_metrics = _geometry_metrics(geometry, polygons)
    instance_count = len(component.insts)
    runtime_bbox = (
        float(bbox[0][0]),
        float(bbox[0][1]),
        float(bbox[1][0]),
        float(bbox[1][1]),
    )
    return {
        "bbox_span_um": [_round_float(value) for value in span],
        "bbox_um": [
            [_round_float(value) for value in bbox[0]],
            [_round_float(value) for value in bbox[1]],
        ],
        "edge_material_intervals": _edge_intervals_for_geometry(
            geometry,
            runtime_bbox,
        ),
        "polygons": polygons,
        "ports": ports,
        "structural_metrics": {
            **source_structural_metrics(source),
            **geometry_metrics,
            "instance_count": int(instance_count),
            "port_count": len(ports),
        },
    }


def _worker(source_path: Path, result_path: Path) -> None:
    source = source_path.read_text(encoding="utf-8")
    record = _runtime_record(source)
    result_path.write_text(
        json.dumps(
            record,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ),
        encoding="utf-8",
    )


def _limited_process() -> None:
    """Apply portable-enough limits in the child immediately before exec."""

    try:
        import resource

        resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
        resource.setrlimit(
            resource.RLIMIT_FSIZE,
            (256 * 1024 * 1024, 256 * 1024 * 1024),
        )
    except (ImportError, OSError, ValueError):
        # Timeout and temporary-directory containment still apply on platforms
        # that do not expose these POSIX limits.
        pass


def _clean_environment(workspace: Path) -> dict[str, str]:
    environment = {
        "HOME": str(workspace / "home"),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "MPLCONFIGDIR": str(workspace / "mpl"),
        "OMP_NUM_THREADS": "1",
        "OPENBLAS_NUM_THREADS": "1",
        "PYTHONHASHSEED": "0",
        "XDG_CACHE_HOME": str(workspace / "cache"),
    }
    for name in ("PATH", "DYLD_LIBRARY_PATH", "LD_LIBRARY_PATH", "PYTHONPATH"):
        if value := os.environ.get(name):
            environment[name] = value
    return environment


def execute_program(
    source: str,
    *,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    isolation: str = "subprocess",
) -> dict[str, Any]:
    """Execute one accepted PixCell program.

    ``isolation="subprocess"`` is the safe default for one-off validation and
    enforces a wall-clock timeout.  ``isolation="in_process"`` avoids repeated
    GDSFactory interpreter startup during a trusted bulk build; callers should
    use it only after the strict purity gate, ideally inside their own
    long-lived process-pool workers.  An in-process call cannot enforce the
    timeout argument.
    """

    if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be finite and positive")
    sanitized = sanitize_source(source)
    if isolation == "in_process":
        result = _runtime_record(sanitized)
        _validate_runtime_record(result)
        return result
    if isolation != "subprocess":
        raise ValueError("isolation must be 'subprocess' or 'in_process'")
    runtime_path = Path(__file__).resolve()
    with tempfile.TemporaryDirectory(prefix="pixcell-depth-runtime-") as raw:
        workspace = Path(raw)
        for directory in ("cache", "home", "mpl"):
            (workspace / directory).mkdir()
        source_path = workspace / "program.py"
        result_path = workspace / "result.json"
        source_path.write_text(sanitized, encoding="utf-8")
        command = [
            sys.executable,
            str(runtime_path),
            "--worker",
            str(source_path),
            str(result_path),
        ]
        try:
            completed = subprocess.run(
                command,
                cwd=workspace,
                env=_clean_environment(workspace),
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
                start_new_session=True,
                preexec_fn=_limited_process if os.name == "posix" else None,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeGateError(
                f"program execution exceeded {timeout_seconds:g}s"
            ) from exc
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout)[-MAX_STDERR_CHARS:]
            raise RuntimeGateError(
                f"program execution failed ({completed.returncode}): {detail}"
            )
        if not result_path.is_file():
            raise RuntimeGateError("program execution omitted its runtime record")
        try:
            result = json.loads(result_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeGateError("program emitted a malformed runtime record") from exc
    _validate_runtime_record(result)
    return result


def _validate_runtime_record(result: Mapping[str, Any]) -> None:
    bbox = result.get("bbox_um")
    if (
        not isinstance(bbox, list)
        or len(bbox) != 2
        or any(not isinstance(point, list) or len(point) != 2 for point in bbox)
    ):
        raise RuntimeGateError("runtime record has no valid bbox")
    values = [float(value) for point in bbox for value in point]
    if not all(math.isfinite(value) for value in values):
        raise RuntimeGateError("runtime bbox contains non-finite values")
    if values[0] >= values[2] or values[1] >= values[3]:
        raise RuntimeGateError("runtime bbox has non-positive extent")
    polygons = result.get("polygons")
    if not isinstance(polygons, list) or not polygons:
        raise RuntimeGateError("runtime record has no polygons")
    ports = result.get("ports")
    if not isinstance(ports, list):
        raise RuntimeGateError("runtime record has no port list")
    metrics = result.get("structural_metrics")
    if not isinstance(metrics, dict) or metrics.get("polygon_count") != len(polygons):
        raise RuntimeGateError("runtime structural metrics disagree with polygons")
    geometry = _geometry_from_polygons(polygons)
    expected_bounds = tuple(_round_float(value) for value in geometry.bounds)
    if any(
        not math.isclose(observed, expected, rel_tol=0.0, abs_tol=1e-6)
        for observed, expected in zip(values, expected_bounds, strict=True)
    ):
        raise RuntimeGateError("runtime bbox differs from material polygon bounds")
    span = result.get("bbox_span_um")
    expected_span = (
        _round_float(expected_bounds[2] - expected_bounds[0]),
        _round_float(expected_bounds[3] - expected_bounds[1]),
    )
    if (
        not isinstance(span, list)
        or len(span) != 2
        or any(
            not math.isclose(
                float(observed),
                expected,
                rel_tol=0.0,
                abs_tol=1e-6,
            )
            for observed, expected in zip(span, expected_span, strict=True)
        )
    ):
        raise RuntimeGateError("runtime span differs from material polygon bounds")
    expected_metrics = _geometry_metrics(geometry, polygons)
    for key, expected in expected_metrics.items():
        if metrics.get(key) != expected:
            raise RuntimeGateError(
                f"runtime structural metric differs from polygons: {key}"
            )


def _as_polygon(record: Mapping[str, Any]) -> Any:
    exterior = record.get("exterior")
    holes = record.get("holes", [])
    if not isinstance(exterior, list) or len(exterior) < 3:
        raise RuntimeGateError("malformed polygon exterior")
    polygon = Polygon(exterior, holes)
    if polygon.is_empty:
        raise RuntimeGateError("empty polygon in runtime record")
    return make_valid(polygon) if not polygon.is_valid else polygon


def _geometry_from_polygons(polygons: Iterable[Mapping[str, Any]]) -> Any:
    pieces = [_as_polygon(record) for record in polygons]
    geometry = unary_union(pieces)
    polygon_parts = _polygon_parts(geometry)
    if not polygon_parts:
        raise RuntimeGateError("runtime polygons union to empty material")
    material = unary_union(polygon_parts)
    if material.is_empty:
        raise RuntimeGateError("runtime polygons union to empty material")
    return material


def _polygon_parts(geometry: Any) -> list[Polygon]:
    if isinstance(geometry, Polygon):
        return [geometry]
    if isinstance(geometry, MultiPolygon):
        return list(geometry.geoms)
    if isinstance(geometry, GeometryCollection):
        parts: list[Polygon] = []
        for child in geometry.geoms:
            parts.extend(_polygon_parts(child))
        return parts
    return []


def _line_parts(geometry: Any) -> list[LineString]:
    if isinstance(geometry, LineString):
        return [geometry]
    if isinstance(geometry, MultiLineString):
        return list(geometry.geoms)
    if isinstance(geometry, GeometryCollection):
        parts: list[LineString] = []
        for child in geometry.geoms:
            parts.extend(_line_parts(child))
        return parts
    return []


def _edge_intervals_for_geometry(
    geometry: Any,
    bounds: tuple[float, float, float, float],
) -> dict[str, list[dict[str, float]]]:
    """Return material cross-sections exposed on each bbox edge.

    These intervals are geometry-derived rather than port-derived.  A builder
    can therefore use them to update literal L4 ``optical_port_specs`` after a
    body mutation, before the declared ports have been repaired.
    """

    min_x, min_y, max_x, max_y = bounds
    span = max(max_x - min_x, max_y - min_y)
    extension = max(0.01, span * 1e-6)
    lines = {
        "bottom": LineString(
            [(min_x - extension, min_y), (max_x + extension, min_y)]
        ),
        "left": LineString(
            [(min_x, min_y - extension), (min_x, max_y + extension)]
        ),
        "right": LineString(
            [(max_x, min_y - extension), (max_x, max_y + extension)]
        ),
        "top": LineString(
            [(min_x - extension, max_y), (max_x + extension, max_y)]
        ),
    }
    records: dict[str, list[dict[str, float]]] = {}
    for side, line in lines.items():
        intervals: list[dict[str, float]] = []
        for segment in _line_parts(geometry.intersection(line)):
            coordinates = list(segment.coords)
            if len(coordinates) < 2:
                continue
            axis = 1 if side in {"left", "right"} else 0
            low = min(float(point[axis]) for point in coordinates)
            high = max(float(point[axis]) for point in coordinates)
            if high - low <= 1e-9:
                continue
            intervals.append(
                {
                    "center_um": _round_float((low + high) / 2),
                    "high_um": _round_float(high),
                    "low_um": _round_float(low),
                    "width_um": _round_float(high - low),
                }
            )
        records[side] = sorted(
            intervals,
            key=lambda item: (item["center_um"], item["width_um"]),
        )
    return records


def edge_material_intervals(
    result: Mapping[str, Any],
) -> dict[str, list[dict[str, float]]]:
    """Recompute geometry-derived terminal candidates on the four bbox edges."""

    _validate_runtime_record(result)
    return _edge_intervals_for_geometry(
        _geometry_from_polygons(result["polygons"]),
        _bounds(result),
    )


def _geometry_metrics(
    geometry: Any,
    polygons: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    parts = _polygon_parts(geometry)
    vertex_count = 0
    for record in polygons:
        vertex_count += len(record["exterior"])
        vertex_count += sum(len(hole) for hole in record.get("holes", []))
    hole_count = sum(
        Polygon(interior).area >= MIN_VISIBLE_HOLE_AREA_UM2
        for part in parts
        for interior in part.interiors
    )
    min_x, min_y, max_x, max_y = geometry.bounds
    bbox_area = (max_x - min_x) * (max_y - min_y)
    layers = {
        tuple(int(value) for value in record["layer"]) for record in polygons
    }
    return {
        "connected_component_count": len(parts),
        "fill_fraction": _round_float(geometry.area / bbox_area),
        "hole_count": hole_count,
        "layer_count": len(layers),
        "material_area_um2": _round_float(geometry.area),
        "polygon_count": len(polygons),
        "vertex_count": vertex_count,
    }


def _bounds(
    result: Mapping[str, Any],
) -> tuple[float, float, float, float]:
    bbox = result["bbox_um"]
    return (
        float(bbox[0][0]),
        float(bbox[0][1]),
        float(bbox[1][0]),
        float(bbox[1][1]),
    )


def _expanded_bounds(
    bounds: tuple[float, float, float, float],
    *,
    padding_fraction: float,
) -> tuple[float, float, float, float]:
    min_x, min_y, max_x, max_y = bounds
    span_x = max_x - min_x
    span_y = max_y - min_y
    if span_x <= 0 or span_y <= 0:
        raise RuntimeGateError("cannot render a non-positive bbox")
    return (
        min_x - span_x * padding_fraction,
        min_y - span_y * padding_fraction,
        max_x + span_x * padding_fraction,
        max_y + span_y * padding_fraction,
    )


def _render_transform(
    bounds: tuple[float, float, float, float],
    *,
    mode: str,
    maximum_canvas_px: tuple[int, int],
    physical_long_edge_px: int,
    margin_px: int,
) -> tuple[tuple[int, int], tuple[float, float]]:
    min_x, min_y, max_x, max_y = bounds
    span_x = max_x - min_x
    span_y = max_y - min_y
    if mode == "maximum_visibility":
        width, height = maximum_canvas_px
        if min(width, height) <= 2 * margin_px:
            raise ValueError("maximum-visibility canvas is smaller than its margins")
        return (width, height), (
            (width - 2 * margin_px) / span_x,
            (height - 2 * margin_px) / span_y,
        )
    if mode != "physical_aspect":
        raise ValueError(
            "mode must be 'maximum_visibility' or 'physical_aspect'"
        )
    if physical_long_edge_px <= 2 * margin_px:
        raise ValueError("physical long edge is smaller than its margins")
    scale = (physical_long_edge_px - 2 * margin_px) / max(span_x, span_y)
    width = max(2 * margin_px + 1, int(math.ceil(span_x * scale)) + 2 * margin_px)
    height = max(
        2 * margin_px + 1,
        int(math.ceil(span_y * scale)) + 2 * margin_px,
    )
    return (width, height), (scale, scale)


def _draw_geometry(
    geometry: Any,
    *,
    canvas: tuple[int, int],
    bounds: tuple[float, float, float, float],
    scale: tuple[float, float],
    margin_px: int,
) -> Image.Image:
    width, height = canvas
    min_x, min_y, _max_x, _max_y = bounds
    scale_x, scale_y = scale

    def pixel(point: Sequence[float]) -> tuple[int, int]:
        return (
            int(round(margin_px + (float(point[0]) - min_x) * scale_x)),
            int(round(height - margin_px - (float(point[1]) - min_y) * scale_y)),
        )

    material = Image.new("1", canvas, color=0)
    for polygon in _polygon_parts(geometry):
        piece = Image.new("1", canvas, color=0)
        draw = ImageDraw.Draw(piece)
        draw.polygon([pixel(point) for point in polygon.exterior.coords], fill=1)
        for interior in polygon.interiors:
            draw.polygon([pixel(point) for point in interior.coords], fill=0)
        material = ImageChops.logical_or(material, piece)
    image = Image.new("L", canvas, color=255)
    image.paste(0, mask=material)
    return image


def _png_bytes(image: Image.Image) -> bytes:
    output = io.BytesIO()
    image.save(output, format="PNG", compress_level=9, optimize=False)
    return output.getvalue()


def render_geometry(
    result: Mapping[str, Any],
    *,
    mode: str,
    world_bounds_um: tuple[float, float, float, float] | None = None,
    maximum_canvas_px: tuple[int, int] = (1440, 1440),
    physical_long_edge_px: int = 2496,
    margin_px: int = 64,
    padding_fraction: float = 0.0,
) -> RenderedPNG:
    """Render flattened material as a deterministic black-on-white PNG.

    Maximum visibility intentionally uses independent x/y scales.  The physical
    view uses exactly one isotropic scale.  The returned transform makes that
    distinction explicit to downstream row construction.
    """

    _validate_runtime_record(result)
    geometry = _geometry_from_polygons(result["polygons"])
    base_bounds = world_bounds_um or _bounds(result)
    bounds = _expanded_bounds(base_bounds, padding_fraction=padding_fraction)
    canvas, scale = _render_transform(
        bounds,
        mode=mode,
        maximum_canvas_px=maximum_canvas_px,
        physical_long_edge_px=physical_long_edge_px,
        margin_px=margin_px,
    )
    image = _draw_geometry(
        geometry,
        canvas=canvas,
        bounds=bounds,
        scale=scale,
        margin_px=margin_px,
    )
    mask = np.asarray(image) < 128
    if not mask.any():
        raise RuntimeGateError("renderer emitted a blank image")
    return RenderedPNG(
        png_bytes=_png_bytes(image),
        mode=mode,
        canvas_px=canvas,
        world_bounds_um=bounds,
        scale_px_per_um=scale,
        margin_px=margin_px,
    )


def render_views(
    result: Mapping[str, Any],
    *,
    maximum_canvas_px: tuple[int, int] = (1440, 1440),
    physical_long_edge_px: int = 2496,
    margin_px: int = 64,
) -> dict[str, RenderedPNG]:
    """Render both row views with explicit calibration metadata."""

    return {
        "maximum_visibility": render_geometry(
            result,
            mode="maximum_visibility",
            maximum_canvas_px=maximum_canvas_px,
            physical_long_edge_px=physical_long_edge_px,
            margin_px=margin_px,
        ),
        "physical_aspect": render_geometry(
            result,
            mode="physical_aspect",
            maximum_canvas_px=maximum_canvas_px,
            physical_long_edge_px=physical_long_edge_px,
            margin_px=margin_px,
        ),
    }


def png_mask(value: bytes | Image.Image | np.ndarray) -> np.ndarray:
    """Convert a runtime PNG/image/array to a boolean material mask."""

    if isinstance(value, bytes):
        with Image.open(io.BytesIO(value)) as opened:
            array = np.asarray(opened.convert("L"))
    elif isinstance(value, Image.Image):
        array = np.asarray(value.convert("L"))
    else:
        array = np.asarray(value)
        if array.ndim == 3:
            array = array[..., :3].mean(axis=2)
    if array.ndim != 2:
        raise ValueError("mask input must resolve to a two-dimensional image")
    return array < 128


def mask_delta(
    reference: bytes | Image.Image | np.ndarray,
    candidate: bytes | Image.Image | np.ndarray,
) -> MaskDelta:
    """Compute IoU and XOR delta for two already aligned rasters."""

    left = png_mask(reference)
    right = png_mask(candidate)
    if left.shape != right.shape:
        raise ValueError(f"mask shapes disagree: {left.shape} != {right.shape}")
    union = np.logical_or(left, right)
    intersection = np.logical_and(left, right)
    changed = np.logical_xor(left, right)
    union_pixels = int(union.sum())
    if union_pixels == 0:
        raise RuntimeGateError("cannot compare two blank masks")
    return MaskDelta(
        iou=float(intersection.sum() / union_pixels),
        changed_fraction=float(changed.sum() / union_pixels),
        xor_pixels=int(changed.sum()),
        union_pixels=union_pixels,
        reference_pixels=int(left.sum()),
        candidate_pixels=int(right.sum()),
    )


def compare_geometry_masks(
    reference: Mapping[str, Any],
    candidate: Mapping[str, Any],
    *,
    mode: str = "physical_aspect",
    maximum_canvas_px: tuple[int, int] = (1440, 1440),
    physical_long_edge_px: int = 2496,
    margin_px: int = 64,
    padding_fraction: float = 0.02,
) -> MaskDelta:
    """Compare two executions after rasterizing into one shared world frame."""

    left = _bounds(reference)
    right = _bounds(candidate)
    shared = (
        min(left[0], right[0]),
        min(left[1], right[1]),
        max(left[2], right[2]),
        max(left[3], right[3]),
    )
    shared = _expanded_bounds(shared, padding_fraction=padding_fraction)
    rendered_left = render_geometry(
        reference,
        mode=mode,
        world_bounds_um=shared,
        maximum_canvas_px=maximum_canvas_px,
        physical_long_edge_px=physical_long_edge_px,
        margin_px=margin_px,
    )
    rendered_right = render_geometry(
        candidate,
        mode=mode,
        world_bounds_um=shared,
        maximum_canvas_px=maximum_canvas_px,
        physical_long_edge_px=physical_long_edge_px,
        margin_px=margin_px,
    )
    return mask_delta(rendered_left.png_bytes, rendered_right.png_bytes)


def compare_masks(
    reference: Mapping[str, Any],
    candidate: Mapping[str, Any],
    **kwargs: Any,
) -> MaskDelta:
    """Compatibility spelling for the shared-frame geometry comparison."""

    return compare_geometry_masks(reference, candidate, **kwargs)


def _port_values(port: Mapping[str, Any]) -> tuple[str, float, float, float, float]:
    try:
        name = str(port["name"])
        center_x, center_y = (float(value) for value in port["center"])
        orientation = float(port["orientation"]) % 360.0
        width = float(port["width"])
    except (KeyError, TypeError, ValueError) as exc:
        raise RuntimeGateError(f"malformed runtime port: {port!r}") from exc
    if (
        not name
        or not all(
            math.isfinite(value)
            for value in (center_x, center_y, orientation, width)
        )
        or width <= 0
    ):
        raise RuntimeGateError(f"malformed runtime port: {port!r}")
    return name, center_x, center_y, orientation, width


def _port_side(
    port: Mapping[str, Any],
    bounds: tuple[float, float, float, float],
) -> str | None:
    _name, center_x, center_y, orientation, width = _port_values(port)
    angle = math.radians(orientation)
    direction = (math.cos(angle), math.sin(angle))
    tangent = (-direction[1], direction[0])
    endpoints = [
        (
            center_x + sign * tangent[0] * width / 2,
            center_y + sign * tangent[1] * width / 2,
        )
        for sign in (-1.0, 1.0)
    ]
    min_x, min_y, max_x, max_y = bounds
    span = max(max_x - min_x, max_y - min_y)
    tolerance = max(0.003, span * 1e-6)
    contracts = {
        "bottom": (1, min, min_y, (0.0, -1.0)),
        "left": (0, min, min_x, (-1.0, 0.0)),
        "right": (0, max, max_x, (1.0, 0.0)),
        "top": (1, max, max_y, (0.0, 1.0)),
    }
    matches: list[tuple[float, str]] = []
    for side, (axis, extreme, boundary, normal) in contracts.items():
        edge = extreme(point[axis] for point in endpoints)
        outward = direction[0] * normal[0] + direction[1] * normal[1]
        if abs(edge - boundary) <= tolerance and outward > 1e-6:
            matches.append((outward, side))
    if not matches:
        return None
    strongest = max(item[0] for item in matches)
    return sorted(
        side
        for outward, side in matches
        if math.isclose(outward, strongest, abs_tol=1e-9)
    )[0]


def _material_probe_fraction(
    port: Mapping[str, Any],
    geometry: Any,
    *,
    inward: bool,
) -> float:
    _name, center_x, center_y, orientation, width = _port_values(port)
    angle = math.radians(orientation)
    outward = (math.cos(angle), math.sin(angle))
    tangent = (-outward[1], outward[0])
    depth = max(0.004, min(0.1, width * 0.15))
    half_width = width * 0.4
    points = [
        (
            center_x + tangent[0] * sign * half_width,
            center_y + tangent[1] * sign * half_width,
        )
        for sign in (-1.0, 1.0)
    ]
    direction = -1.0 if inward else 1.0
    points.extend(
        (
            center_x
            + direction * outward[0] * depth
            + tangent[0] * sign * half_width,
            center_y
            + direction * outward[1] * depth
            + tangent[1] * sign * half_width,
        )
        for sign in (1.0, -1.0)
    )
    probe = Polygon(points)
    if probe.is_empty or probe.area <= 0:
        return 0.0
    return float(geometry.intersection(probe).area / probe.area)


def _orientation_side(orientation: float) -> str:
    angle = math.radians(orientation)
    direction = (math.cos(angle), math.sin(angle))
    candidates = {
        "bottom": -direction[1],
        "left": -direction[0],
        "right": direction[0],
        "top": direction[1],
    }
    strongest = max(candidates.values())
    return sorted(
        side
        for side, component in candidates.items()
        if math.isclose(component, strongest, rel_tol=0.0, abs_tol=1e-12)
    )[0]


def _orientation_label(orientation: float) -> str:
    nearest = min(
        CARDINAL_ANGLES,
        key=lambda candidate: abs(
            (orientation - candidate + 180.0) % 360.0 - 180.0
        ),
    )
    delta = abs((orientation - nearest + 180.0) % 360.0 - 180.0)
    if delta <= 0.01:
        return f"{int(nearest):03d}"
    return f"{_round_float(orientation):07.3f}"


def _port_tangent_coordinate(
    port: Mapping[str, Any],
    side: str,
) -> float:
    _name, center_x, center_y, _orientation, _width = _port_values(port)
    return center_y if side in {"left", "right"} else center_x


def _ordered_interval_partition(
    intervals: Sequence[Mapping[str, float]],
    anchor_ports: Sequence[Mapping[str, Any]],
    *,
    side: str,
    anchor_bounds: tuple[float, float, float, float],
    candidate_bounds: tuple[float, float, float, float],
) -> list[list[Mapping[str, float]]]:
    """Partition ordered edge segments into ordered anchor terminals."""

    count = len(anchor_ports)
    if len(intervals) < count:
        raise RuntimeGateError(
            f"{side}: found {len(intervals)} material intervals for "
            f"{count} anchor ports"
        )
    if len(intervals) == count:
        return [[interval] for interval in intervals]
    tangent_axis = 1 if side in {"left", "right"} else 0
    anchor_low = anchor_bounds[tangent_axis]
    anchor_high = anchor_bounds[tangent_axis + 2]
    candidate_low = candidate_bounds[tangent_axis]
    candidate_high = candidate_bounds[tangent_axis + 2]
    anchor_span = anchor_high - anchor_low
    candidate_span = candidate_high - candidate_low
    targets: list[tuple[float, float]] = []
    for port in anchor_ports:
        coordinate = _port_tangent_coordinate(port, side)
        _name, _x, _y, _orientation, width = _port_values(port)
        fraction = (coordinate - anchor_low) / anchor_span
        targets.append(
            (
                candidate_low + fraction * candidate_span,
                width * candidate_span / anchor_span,
            )
        )

    # Dynamic programming over contiguous partitions.  Contiguity preserves
    # terminal ordering while allowing one logical slot port to span several
    # disjoint material rails.
    memo: dict[tuple[int, int], tuple[float, list[list[Mapping[str, float]]]]] = {}

    def solve(
        interval_index: int,
        port_index: int,
    ) -> tuple[float, list[list[Mapping[str, float]]]]:
        key = (interval_index, port_index)
        if key in memo:
            return memo[key]
        remaining_ports = count - port_index
        remaining_intervals = len(intervals) - interval_index
        if remaining_ports == 0:
            return (0.0, []) if remaining_intervals == 0 else (math.inf, [])
        best: tuple[float, list[list[Mapping[str, float]]]] = (math.inf, [])
        max_take = remaining_intervals - (remaining_ports - 1)
        target_center, target_width = targets[port_index]
        for take in range(1, max_take + 1):
            group = list(intervals[interval_index : interval_index + take])
            low = min(float(item["low_um"]) for item in group)
            high = max(float(item["high_um"]) for item in group)
            center = (low + high) / 2
            width = high - low
            scale = max(candidate_span, 1e-9)
            width_scale = max(target_width, scale * 1e-6)
            group_cost = abs(center - target_center) / scale
            group_cost += 0.25 * abs(width - target_width) / width_scale
            tail_cost, tail = solve(interval_index + take, port_index + 1)
            total = group_cost + tail_cost
            if total < best[0]:
                best = (total, [group, *tail])
        memo[key] = best
        return best

    cost, groups = solve(0, 0)
    if not math.isfinite(cost) or len(groups) != count:
        raise RuntimeGateError(f"{side}: could not assign boundary intervals")
    return groups


def derive_optical_port_specs(
    anchor: Mapping[str, Any],
    candidate: Mapping[str, Any],
) -> tuple[tuple[str, tuple[float, float], float, float], ...]:
    """Derive candidate L4 ``optical_port_specs`` from material boundaries.

    Names, orientation, side, and ordering come from the approved anchor.
    Centers and widths come from candidate boundary material, including a
    deterministic contiguous grouping when one logical port spans multiple
    rails (slot/subwavelength terminals).  The tuple shape exactly matches the
    literal used by all core-v1 L4 programs.
    """

    _validate_runtime_record(anchor)
    _validate_runtime_record(candidate)
    anchor_bounds = _bounds(anchor)
    candidate_bounds = _bounds(candidate)
    anchor_by_side: dict[str, list[Mapping[str, Any]]] = {
        side: [] for side in ("bottom", "left", "right", "top")
    }
    for port in anchor["ports"]:
        side = _port_side(port, anchor_bounds)
        name, _x, _y, orientation, _width = _port_values(port)
        if side is None:
            raise RuntimeGateError(
                f"anchor port {name} at {orientation:g} degrees is not a bbox terminal"
            )
        anchor_by_side[side].append(port)
    for side in anchor_by_side:
        anchor_by_side[side].sort(
            key=lambda port: (
                _port_tangent_coordinate(port, side),
                _port_values(port)[0],
            )
        )

    intervals = edge_material_intervals(candidate)
    repaired: dict[str, tuple[str, tuple[float, float], float, float]] = {}
    min_x, min_y, max_x, max_y = candidate_bounds
    for side, ports in anchor_by_side.items():
        if not ports:
            continue
        groups = _ordered_interval_partition(
            intervals[side],
            ports,
            side=side,
            anchor_bounds=anchor_bounds,
            candidate_bounds=candidate_bounds,
        )
        for port, group in zip(ports, groups, strict=True):
            name, _x, _y, orientation, _old_width = _port_values(port)
            low = min(float(item["low_um"]) for item in group)
            high = max(float(item["high_um"]) for item in group)
            center = _round_float((low + high) / 2)
            width = _round_float(high - low)
            if side == "left":
                point = (_round_float(min_x), center)
            elif side == "right":
                point = (_round_float(max_x), center)
            elif side == "bottom":
                point = (center, _round_float(min_y))
            else:
                point = (center, _round_float(max_y))
            repaired[name] = (name, point, width, _round_float(orientation))
    anchor_names = [_port_values(port)[0] for port in anchor["ports"]]
    if set(repaired) != set(anchor_names):
        raise RuntimeGateError(
            "derived port set differs from anchor: "
            f"derived={sorted(repaired)} anchor={sorted(anchor_names)}"
        )
    return tuple(repaired[name] for name in anchor_names)


def gate_ports(
    result: Mapping[str, Any],
    *,
    reference: Mapping[str, Any] | None = None,
    expected_count: int | None = None,
    minimum_contact_fraction: float = 0.50,
    maximum_outward_material_fraction: float | None = None,
    require_bbox_edge: bool = False,
) -> PortGateReport:
    """Gate count, terminal side/orientation, and material attachment.

    When ``reference`` is supplied, the candidate must preserve its count and
    orientation-side histogram.  This deliberately permits parameters to move
    terminals along an edge while rejecting detached, rotated, or re-sided
    terminals.
    """

    _validate_runtime_record(result)
    if not 0.0 <= minimum_contact_fraction <= 1.0:
        raise ValueError("minimum_contact_fraction must lie in [0, 1]")
    if maximum_outward_material_fraction is not None and not (
        0.0 <= maximum_outward_material_fraction <= 1.0
    ):
        raise ValueError("maximum_outward_material_fraction must lie in [0, 1]")
    geometry = _geometry_from_polygons(result["polygons"])
    bounds = _bounds(result)
    ports = list(result["ports"])
    errors: list[str] = []
    names: list[str] = []
    witnesses: list[PortWitness] = []
    signature: Counter[str] = Counter()
    for port in ports:
        name, _x, _y, orientation, width = _port_values(port)
        names.append(name)
        side = _orientation_side(orientation)
        bbox_side = _port_side(port, bounds)
        contact_fraction = _material_probe_fraction(
            port,
            geometry,
            inward=True,
        )
        outward_fraction = _material_probe_fraction(
            port,
            geometry,
            inward=False,
        )
        touches = (
            contact_fraction >= minimum_contact_fraction
            and (
                maximum_outward_material_fraction is None
                or outward_fraction <= maximum_outward_material_fraction
            )
        )
        if require_bbox_edge and bbox_side is None:
            errors.append(f"{name}: terminal is not on its outward bbox side")
        signature[f"{side}:{_orientation_label(orientation)}"] += 1
        if contact_fraction < minimum_contact_fraction:
            errors.append(
                f"{name}: inward material fraction {contact_fraction:.3f} "
                f"< {minimum_contact_fraction:.3f}"
            )
        if (
            maximum_outward_material_fraction is not None
            and outward_fraction > maximum_outward_material_fraction
        ):
            errors.append(
                f"{name}: outward material fraction {outward_fraction:.3f} "
                f"> {maximum_outward_material_fraction:.3f}"
            )
        witnesses.append(
            PortWitness(
                name=name,
                side=side,
                bbox_side=bbox_side,
                orientation_deg=orientation,
                width_um=width,
                inward_material_fraction=contact_fraction,
                outward_material_fraction=outward_fraction,
                touches_material=touches,
            )
        )
    if len(names) != len(set(names)):
        errors.append("runtime port names are not unique")
    if expected_count is not None and len(ports) != expected_count:
        errors.append(
            f"port count mismatch: observed={len(ports)} expected={expected_count}"
        )
    if reference is not None:
        reference_report = gate_ports(
            reference,
            minimum_contact_fraction=minimum_contact_fraction,
            maximum_outward_material_fraction=maximum_outward_material_fraction,
            require_bbox_edge=require_bbox_edge,
        )
        if len(ports) != reference_report.port_count:
            errors.append(
                "port count changed from reference: "
                f"{reference_report.port_count} -> {len(ports)}"
            )
        if dict(signature) != reference_report.orientation_side_histogram:
            errors.append(
                "orientation-side histogram changed from reference: "
                f"{reference_report.orientation_side_histogram} -> "
                f"{dict(sorted(signature.items()))}"
            )
    return PortGateReport(
        passed=not errors,
        errors=tuple(errors),
        port_count=len(ports),
        orientation_side_histogram=dict(sorted(signature.items())),
        witnesses=tuple(witnesses),
    )


def validate_candidate(
    reference: Mapping[str, Any],
    candidate: Mapping[str, Any],
    *,
    minimum_contact_fraction: float = 0.50,
    maximum_outward_material_fraction: float | None = None,
    minimum_changed_fraction: float = 0.002,
    maximum_changed_fraction: float = 0.80,
    comparison_mode: str = "physical_aspect",
    require_same_connected_components: bool = True,
    require_same_holes: bool = True,
    require_bbox_edge_ports: bool = False,
) -> CandidateGateReport:
    """Validate a controlled realization against its representation anchor.

    The gate preserves source grammar, layer count, and reference-operation
    structure; checks the full port contract; and rejects both raster no-ops
    and transformations so large that they are unlikely to be realizations of
    the same representation.  Callers may disable the connected-component
    invariant for a specifically audited count axis.
    """

    _validate_runtime_record(reference)
    _validate_runtime_record(candidate)
    errors: list[str] = []
    ports = gate_ports(
        candidate,
        reference=reference,
        minimum_contact_fraction=minimum_contact_fraction,
        maximum_outward_material_fraction=maximum_outward_material_fraction,
        require_bbox_edge=require_bbox_edge_ports,
    )
    errors.extend(ports.errors)
    left_metrics = reference["structural_metrics"]
    right_metrics = candidate["structural_metrics"]
    preserved = [
        "layer_count",
        "primitive_call_histogram",
        "reference_operation_histogram",
    ]
    if require_same_connected_components:
        preserved.append("connected_component_count")
    if require_same_holes:
        preserved.append("hole_count")
    deltas: dict[str, tuple[Any, Any]] = {}
    for key in preserved:
        before = left_metrics.get(key)
        after = right_metrics.get(key)
        if before != after:
            deltas[key] = (before, after)
            errors.append(f"structural witness changed: {key}={before!r}->{after!r}")
    delta = compare_geometry_masks(
        reference,
        candidate,
        mode=comparison_mode,
    )
    if delta.changed_fraction < minimum_changed_fraction:
        errors.append(
            "candidate is a raster no-op: changed_fraction="
            f"{delta.changed_fraction:.6f} < {minimum_changed_fraction:.6f}"
        )
    if delta.changed_fraction > maximum_changed_fraction:
        errors.append(
            "candidate exceeds the realization delta cap: changed_fraction="
            f"{delta.changed_fraction:.6f} > {maximum_changed_fraction:.6f}"
        )
    return CandidateGateReport(
        passed=not errors,
        errors=tuple(errors),
        port_gate=ports,
        structural_deltas=deltas,
        mask_delta=delta,
    )


def _main() -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("source", nargs="?")
    parser.add_argument("result", nargs="?")
    args = parser.parse_args()
    if not args.worker or not args.source or not args.result:
        parser.error("runtime.py is an importable helper; worker mode is internal")
    try:
        _worker(Path(args.source), Path(args.result))
    except Exception as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
