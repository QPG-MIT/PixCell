"""conductor.gate — the deterministic acceptance check over artifacts (P2).

No worker-reported number enters the record: the gate recomputes IoU from the
GDS, checks the primitives contract by source analysis, and (optionally)
proves the declared knob moves real geometry.
"""

import json
import textwrap

from PIL import Image

from homi.conductor import gate


def test_purity_violations_flags_stencils_and_polygons():
    clean = "import gdsfactory as gf\nc = gf.components.rectangle(size=(10, 2), layer=(1, 0))\n"
    assert gate.purity_violations(clean) == []

    stencil = "c = gf.components.mzi(delta_length=10)\n"
    assert any("mzi" in v for v in gate.purity_violations(stencil))

    raw = "c.add_polygon([(0, 0), (1, 0), (1, 1)], layer=(1, 0))\n"
    assert any("add_polygon" in v for v in gate.purity_violations(raw))


def test_purity_whitelist_rejects_non_catalog_components():
    """The catalog (paper Table 1) is a whitelist: anything else flags."""
    for evasion in (
        "c = gf.components.grating_coupler_elliptical()\n",
        "c = gf.c.mmi1x2()\n",
        "from gdsfactory.components import mzi\n",
        "from gdsfactory.components import rectangle, spiral_racetrack\n",
        "import gdsfactory.components as comps\nc = comps.crossing()\n",
    ):
        assert any("non-catalog" in v for v in gate.purity_violations(evasion)), evasion

    # Permitted primitives must NOT flag — including ring and coupler_straight,
    # which the historical stencil blacklist would have false-flagged.
    for permitted in (
        "c = gf.components.ring(radius=10, width=0.5)\n",
        "c = gf.components.coupler_straight(length=10, gap=0.2)\n",
        "from gdsfactory.components import rectangle as rect\n",
    ):
        assert gate.purity_violations(permitted) == [], permitted


def test_purity_violations_flags_raster_tracers():
    """Re-audit 2026-07-12 (issue #74): image reads and scanline dumps are traces."""
    runtime_read = "from PIL import Image\nmask = Image.open('component.png').convert('L')\n"
    assert any(v.startswith("image-read") for v in gate.purity_violations(runtime_read))

    cv2_read = "import cv2\nmask = cv2.imread('device_bw.png')\n"
    assert any(v.startswith("image-read") for v in gate.purity_violations(cv2_read))

    rows = ",".join(f"({x}, {x + 40}, {y}, {y})" for y in range(30) for x in range(10))
    scanline_dump = f"MASK_ROWS = [{rows}]\n"  # 300 literal coordinate tuples
    assert any(v.startswith("coordinate-dump") for v in gate.purity_violations(scanline_dump))

    flat_dump = f"XS = [{', '.join(str(i) for i in range(1100))}]\n"
    assert any(v.startswith("numeric-dump") for v in gate.purity_violations(flat_dump))


def test_purity_allows_measured_features_and_control_points():
    """Per-feature physical dimensions and path control points stay in contract."""
    teeth = ",".join(f"({4.4 + 0.13 * i:.3f}, {4.52 + 0.13 * i:.3f})" for i in range(112))
    measured = f"import gdsfactory as gf\ntooth_ranges_um = [{teeth}]\n"
    assert gate.purity_violations(measured) == []

    pts = ",".join(f"({2.5 * i:.2f}, {0.3 + 0.01 * i:.2f})" for i in range(48))
    centerline = f"import gdsfactory as gf\npath = gf.path.smooth([{pts}], radius=4)\n"
    assert gate.purity_violations(centerline) == []


def _make_cell(tmp_path):
    """Target PNG + calibration + matching GDS for a 10x2 um rectangle."""
    # Target: black 200x40 block at (10,10) on a 220x60 white canvas -> 20 px/um
    img = Image.new("L", (220, 60), 255)
    img.paste(0, (10, 10, 210, 50))
    target = tmp_path / "component.png"
    img.save(target)

    footprint = tmp_path / "footprint.json"
    footprint.write_text(json.dumps({"footprint_um": [10.0, 2.0]}))

    calib = tmp_path / "calibration.json"
    from homi.jee_integration import prepare_calibration

    prepare_calibration(str(target), str(footprint), str(calib))

    script = tmp_path / "device.py"
    script.write_text(
        textwrap.dedent(
            """
            import gdsfactory as gf

            length_um = 10.0
            width_um = 2.0

            c = gf.components.rectangle(size=(length_um, width_um), layer=(1, 0))
            c.write_gds("device.gds")
            """
        )
    )
    import subprocess
    import sys

    subprocess.run([sys.executable, str(script)], cwd=tmp_path, check=True, timeout=120)
    return tmp_path / "device.gds", target, calib, script


def test_verify_cell_recomputes_and_gates(tmp_path):
    gds, target, calib, script = _make_cell(tmp_path)

    res = gate.verify_cell(gds, target, calib, script)
    assert res.iou > 0.95
    assert res.purity == []
    assert res.verified

    # A claim within tolerance verifies; an inflated claim does not.
    ok = gate.verify_cell(gds, target, calib, script, claimed_iou=res.iou)
    assert ok.iou_matches_claim and ok.verified
    inflated = gate.verify_cell(gds, target, calib, script, claimed_iou=min(1.0, res.iou + 0.05))
    assert inflated.iou_matches_claim is False and not inflated.verified


def test_knob_response_moves_area(tmp_path):
    gds, target, calib, script = _make_cell(tmp_path)

    res = gate.verify_cell(gds, target, calib, script, knob=("length_um", 2.0))
    assert res.knob is not None
    assert res.knob["ok"], res.knob
    assert res.verified
