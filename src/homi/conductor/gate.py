"""The conductor's adversarial acceptance gate.

Promoted from the retired ``.claude/workflows/paper-swap-phase-a.js`` verify
stage and RUNBOOK step 3: no worker-reported number enters the record. The
gate (1) recomputes IoU from the produced GDS with the same metric engine the
worker iterated against, (2) checks the primitives contract by source
analysis, and (3) optionally proves the declared knob moves real geometry.
"""

from __future__ import annotations

import ast
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

#: A recomputed IoU must match the worker's claim within this (workflow JS: 0.005).
IOU_CLAIM_TOLERANCE = 0.005

_PURITY_PATTERNS = (
    r"\badd_polygon\b",
    r"\bfrom_polygon\b",
)

# The permitted component vocabulary (paper Table 1). The historical check was
# a stencil BLACKLIST (mzi|ring|coupler|splitter|mmi families); since the
# 2026-07-12 re-audit the gate enforces the catalog as a WHITELIST instead:
# any other gf.components call is a violation. This also resolves the latent
# blacklist tension where the permitted primitives `ring` and
# `coupler_straight` matched the ring/coupler stencil families.
_CATALOG_COMPONENTS = frozenset({
    "rectangle", "circle", "ring", "cross", "triangle", "ellipse",
    "regular_polygon", "L", "straight", "bend_euler", "bend_circular",
    "bend_s", "taper", "coupler_straight",
})
_COMPONENT_REF = re.compile(r"\b(?:gf|gdsfactory)\.(?:components|c)\.(\w+)")
_COMPONENT_FROM_IMPORT = re.compile(r"from\s+gdsfactory\.components\s+import\s+([^\n]+)")
_COMPONENT_ALIAS = re.compile(r"import\s+gdsfactory\.components\s+as\s+(\w+)")


def _non_catalog_components(source: str) -> list[str]:
    """Whitelist check: every component reference must be in the Table-1 catalog."""
    hits: list[str] = []
    for m in _COMPONENT_REF.finditer(source):
        if m.group(1) not in _CATALOG_COMPONENTS:
            hits.append(f"non-catalog component: {m.group(0)}")
    for m in _COMPONENT_FROM_IMPORT.finditer(source):
        for segment in m.group(1).split(","):
            words = segment.split()
            if not words:
                continue
            name = words[0]
            if name == "*":
                hits.append("non-catalog component import: wildcard")
            elif name not in _CATALOG_COMPONENTS:
                hits.append(f"non-catalog component import: {name}")
    for m in _COMPONENT_ALIAS.finditer(source):
        alias = m.group(1)
        for ref in re.finditer(rf"\b{re.escape(alias)}\.(\w+)", source):
            if ref.group(1) not in _CATALOG_COMPONENTS:
                hits.append(f"non-catalog component: {ref.group(0)}")
    return hits

# Tracer detection (re-audit 2026-07-12, issue #74): six archived cells traced
# their raster instead of constructing geometry — four by reading an image at
# runtime and emitting one rectangle per pixel run, two by embedding the same
# scanline dump as a literal coordinate list. Whitelisted primitives, defeated
# contract. The boundary drawn there: per-feature physical dimensions and path
# control points are within contract (largest compliant cell: 112 coordinate
# tuples / 344 numeric literals); runtime image reads and raster-pitch
# scanline dumps are violations (smallest tracer: ~575 tuples / 2303
# literals). Thresholds sit between with wide margins on both sides.
_IMAGE_READ_PATTERNS = (
    r"(?:from|import)\s+(?:PIL|cv2|imageio|skimage|matplotlib\.image)\b",
    r"\bImage\.open\b",
    r"\bimread\s*\(",
)
_COORD_TUPLE_LIMIT = 256
_NUMERIC_LITERAL_LIMIT = 1024


def _is_number(node: ast.expr) -> bool:
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        node = node.operand
    return isinstance(node, ast.Constant) and isinstance(node.value, (int, float))


def _coordinate_dump_stats(source: str) -> tuple[int, int]:
    """(coordinate tuples summed over all literal lists, total numeric literals)."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return 0, 0
    tuples = 0
    numerics = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            numerics += 1
        if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
            tuples += sum(
                1
                for elt in node.elts
                if isinstance(elt, (ast.Tuple, ast.List))
                and len(elt.elts) >= 2
                and all(_is_number(e) for e in elt.elts)
            )
    return tuples, numerics

# Same top-level `<name> = <number>` pattern homi.spec_optimization uses.
_ASSIGNMENT = r"(\b{name}\s*(?::\s*[^=]+)?\s*=\s*)(-?\d+\.?\d*)"


@dataclass(frozen=True)
class GateResult:
    iou: float
    metrics: dict
    iou_matches_claim: bool | None
    purity: list[str]
    knob: dict | None
    verified: bool


def purity_violations(source: str) -> list[str]:
    """Primitives-contract check by source analysis.

    Rejects non-catalog component calls (Table-1 whitelist), raw polygon
    emission, and — since the 2026-07-12 re-audit (issue #74) — raster
    tracing: runtime image reads inside the device script, and embedded
    scanline dumps (literal coordinate lists far beyond any per-feature
    measurement).
    """
    hits: list[str] = []
    for pattern in _PURITY_PATTERNS:
        hits.extend(m.group(0) for m in re.finditer(pattern, source))
    hits.extend(_non_catalog_components(source))
    for pattern in _IMAGE_READ_PATTERNS:
        hits.extend(f"image-read: {m.group(0)}" for m in re.finditer(pattern, source))
    tuples, numerics = _coordinate_dump_stats(source)
    if tuples >= _COORD_TUPLE_LIMIT:
        hits.append(f"coordinate-dump: {tuples} literal coordinate tuples")
    if numerics >= _NUMERIC_LITERAL_LIMIT:
        hits.append(f"numeric-dump: {numerics} numeric literals")
    return hits


def recompute_metrics(gds: Path | str, target_png: Path | str, calibration: Path | str) -> dict:
    """Re-rasterize the GDS at calibrated absolute scale and rescore it."""
    from michaelangelo.core.compare_absolute import (
        compute_metrics,
        extract_polygons,
        load_calibration,
        render_gds_absolute,
    )

    polygons = extract_polygons(str(gds))
    calib = load_calibration(str(calibration))
    raster, _render_info = render_gds_absolute(polygons, calib)
    target = Image.open(str(target_png))
    return compute_metrics(raster, target)


def _layer_area(gds_path: Path, layer: tuple[int, int] = (1, 0)) -> float:
    """Layer polygon area from a written GDS, robust to kfactory cell shapes.

    kfactory's ``$$$CONTEXT_INFO$$$`` metadata cell REFERENCES every cell in
    the library, so naive top-cell traversal through it double-counts. The
    true device tops are the non-metadata cells that no other non-metadata
    cell references.
    """
    import gdstk

    library = gdstk.read_gds(str(gds_path))
    real = [c for c in library.cells if "$$$" not in c.name]
    referenced = set()
    for cell in real:
        for ref in cell.references:
            child = getattr(ref, "cell", None)
            name = getattr(child, "name", child if isinstance(child, str) else None)
            if name:
                referenced.add(name)
    tops = [c for c in real if c.name not in referenced] or library.top_level()
    total = 0.0
    for cell in tops:
        for polygon in cell.get_polygons(depth=None, layer=layer[0], datatype=layer[1]):
            total += polygon.area()
    return total


def knob_response(
    script: Path | str,
    param: str,
    width_um: float | None = None,
    delta_um: float = 5.0,
    timeout_s: int = 180,
) -> dict:
    """Prove the top-level knob moves real geometry (anti-fake check).

    Self-contained variant of ``homi.spec_optimization.verify_knob_response``
    that does not require the script to write ``lengths.json``: perturb the
    ``<param> = <number>`` assignment by ``delta_um``, rebuild, and require the
    layer-(1,0) area to move — and, when ``width_um`` is given, to move by
    ~``width_um * delta_um`` within 25%.
    """
    script = Path(script).resolve()
    source = script.read_text()
    pattern = _ASSIGNMENT.format(name=re.escape(param))
    match = re.search(pattern, source)
    if match is None:
        return {"param": param, "ok": False,
                "error": f"no top-level '{param} = <number>' assignment in {script.name}"}
    base_value = float(match.group(2))
    perturbed = re.sub(pattern, rf"\g<1>{base_value + delta_um}", source)

    def _build(variant_source: str, tag: str, tmp: Path) -> float:
        run_dir = tmp / tag
        run_dir.mkdir(parents=True)
        copy = run_dir / script.name
        copy.write_text(variant_source)
        subprocess.run(
            [sys.executable, str(copy)], cwd=run_dir, check=True,
            capture_output=True, timeout=timeout_s,
        )
        gds_files = sorted(run_dir.glob("*.gds"), key=lambda p: p.stat().st_mtime)
        if not gds_files:
            raise RuntimeError(f"{tag}: script wrote no GDS")
        return _layer_area(gds_files[-1])

    try:
        with tempfile.TemporaryDirectory(prefix="gate_knob_") as tmp:
            base_area = _build(source, "base", Path(tmp))
            pert_area = _build(perturbed, "perturbed", Path(tmp))
    except Exception as e:  # noqa: BLE001 — a knob check that cannot run is a failed check
        return {"param": param, "ok": False, "error": str(e)}

    growth = pert_area - base_area
    result = {
        "param": param, "delta_um": delta_um, "base_area_um2": base_area,
        "perturbed_area_um2": pert_area, "area_growth_um2": growth,
    }
    if width_um is not None:
        expected = width_um * delta_um
        result["expected_area_growth_um2"] = expected
        result["ok"] = abs(growth - expected) <= 0.25 * abs(expected)
    else:
        result["ok"] = abs(growth) > 1e-6
    return result


def verify_cell(
    gds: Path | str,
    target_png: Path | str,
    calibration: Path | str,
    script: Path | str,
    claimed_iou: float | None = None,
    knob: tuple[str, float] | None = None,
) -> GateResult:
    """The full adversarial gate over one cell's artifacts.

    ``knob`` is ``(param_name, guide_width_um)`` — pass it to also require the
    declared knob to move real geometry.
    """
    metrics = recompute_metrics(gds, target_png, calibration)
    iou = float(metrics["IoU"])
    matches = None if claimed_iou is None else abs(iou - float(claimed_iou)) <= IOU_CLAIM_TOLERANCE
    purity = purity_violations(Path(script).read_text())
    knob_result = knob_response(script, knob[0], width_um=knob[1]) if knob else None
    verified = (
        not purity
        and matches is not False
        and (knob_result is None or bool(knob_result.get("ok")))
    )
    return GateResult(
        iou=iou, metrics=metrics, iou_matches_claim=matches,
        purity=purity, knob=knob_result, verified=verified,
    )
