"""The conductor's adversarial acceptance gate.

Promoted from the retired ``.claude/workflows/paper-swap-phase-a.js`` verify
stage and RUNBOOK step 3: no worker-reported number enters the record. The
gate (1) recomputes IoU from the produced GDS with the same metric engine the
worker iterated against, (2) checks the primitives contract by source
analysis, and (3) optionally proves the declared knob moves real geometry.
"""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from homi.conductor.source_policy import purity_violations

#: A recomputed IoU must match the worker's claim within this (workflow JS: 0.005).
IOU_CLAIM_TOLERANCE = 0.005

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
