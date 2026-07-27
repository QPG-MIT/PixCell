"""The device workbench generator (P: workbench redesign).

The generated notebook is the product surface — it must be a valid marimo
file, self-contained (no unresolved template sentinels), and honest (only
consumed knobs become sliders).
"""

import ast
import base64
import json
import subprocess
import sys
import textwrap
from pathlib import Path

CONTRACT_SCRIPT = textwrap.dedent(
    """
    import gdsfactory as gf

    layer = (1, 0)
    length_um = 10.0
    width_um = 2.0
    unused_note_um = 99.0

    @gf.cell
    def device() -> gf.Component:
        c = gf.Component()
        r = gf.components.rectangle(size=(length_um, width_um), layer=layer)
        c.add_ref(r)
        return c

    if __name__ == "__main__":
        device().write_gds("device.gds")
    """
)


def _project(tmp_path):
    project = tmp_path / "devx"
    out = project / "output"
    out.mkdir(parents=True)
    (out / "best.py").write_text(CONTRACT_SCRIPT)
    (project / "footprint.json").write_text(json.dumps({"footprint_um": [10.0, 2.0]}))
    return out / "best.py"


def _embedded_assignment(notebook_text, name):
    tree = ast.parse(notebook_text)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if any(isinstance(target, ast.Name) and target.id == name
               for target in node.targets):
            return ast.literal_eval(node.value)
    raise AssertionError(f"generated notebook has no {name} assignment")


def test_generate_workbench_play_variant(tmp_path):
    from homi.workbench import generate_workbench

    script = _project(tmp_path)
    nb = generate_workbench(script)
    text = nb.read_text()

    ast.parse(text)                       # valid python
    assert "__PARAMS__" not in text       # no unresolved sentinels
    assert "__CSS__" not in text
    assert "'devx'" in text               # device name from the project dir
    assert "length_um" in text and "width_um" in text
    assert "unused_note_um" not in text or "'unused_note_um'" not in text.split(
        "PARAMS = ")[1].split("\n")[0]    # unused knob filtered from sliders
    assert "Dispatch recreation worker" not in text  # play variant: no Draw tab


def test_generated_workbench_uses_concise_neutral_labels(tmp_path):
    from homi.workbench import generate_workbench

    text = generate_workbench(_project(tmp_path)).read_text()

    assert "Function parameters" in text
    assert "Additional parameters" in text
    assert "Artifact record" in text
    assert "why you can trust this device" not in text
    assert "Knobs · function-defining" not in text
    assert "more knobs" not in text
    assert "Current knob values" not in text
    assert "Export GDS (current knobs)" not in text


def test_gate_record_overrides_recreation_metrics_in_provenance(tmp_path):
    from homi.workbench import generate_workbench

    script = _project(tmp_path)
    recreation = script.parent / "recreation_legacy"
    recreation.mkdir()
    (recreation / "metrics_abs.json").write_text(json.dumps({
        "IoU": 0.12,
        "Dice": 0.21,
    }))
    (script.parent / "gate.json").write_text(json.dumps({
        "verified": True,
        "promoted": False,
        "iou": 0.91,
        "metrics": {"IoU": 0.91, "Dice": 0.95},
        "claim": "missing",
        "claimed_iou": None,
        "purity": [],
        "knob_status": "missing",
        "strict": True,
        "reasons": ["no submission.json claim (strict gate)"],
    }))

    provenance = _embedded_assignment(
        generate_workbench(script).read_text(), "PROVENANCE")

    assert provenance["iou"] == 0.91
    assert provenance["dice"] == 0.95
    assert provenance["verified"] is True
    assert provenance["promoted"] is False
    assert provenance["claim"] == "missing"
    assert provenance["knob_status"] == "missing"
    assert provenance["source"] == "output/gate.json"


def test_recreation_metrics_remain_provenance_fallback(tmp_path):
    from homi.workbench import generate_workbench

    script = _project(tmp_path)
    recreation = script.parent / "recreation_legacy"
    recreation.mkdir()
    (recreation / "metrics_abs.json").write_text(json.dumps({
        "IoU": 0.72,
        "Dice": 0.81,
    }))

    provenance = _embedded_assignment(
        generate_workbench(script).read_text(), "PROVENANCE")

    assert provenance["iou"] == 0.72
    assert provenance["dice"] == 0.81
    assert provenance["source"] == "output/recreation_legacy/metrics_abs.json"


def test_generate_workbench_draw_variant(tmp_path):
    from homi.workbench import generate_workbench

    script = _project(tmp_path)
    nb = generate_workbench(script, draw=True)
    text = nb.read_text()
    ast.parse(text)
    assert "Dispatch recreation worker" in text
    assert "mo.ui.radio" in text          # mode switch, NOT mo.ui.tabs (clones)
    assert "mo.ui.tabs(" not in text      # (the comment explaining why is fine)


def test_generated_notebook_passes_marimo_check(tmp_path):
    from homi.workbench import generate_workbench

    script = _project(tmp_path)
    nb = generate_workbench(script, draw=True)
    marimo = Path(sys.executable).parent / "marimo"
    proc = subprocess.run(
        [str(marimo), "check", str(nb)], capture_output=True, text=True, timeout=120
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_generated_notebook_embeds_target_for_portable_download(tmp_path):
    from PIL import Image

    from homi.workbench import generate_workbench

    script = _project(tmp_path)
    recreation = script.parent / "recreation_portable"
    recreation.mkdir()
    target = recreation / "component.png"
    Image.new("L", (4, 3), 255).save(target)
    (recreation / "calibration.json").write_text(json.dumps({
        "image_size_px": [4, 3],
        "scale_px_per_um": [0.4, 1.5],
        "offset": [0, 0],
        "white_threshold": 245,
    }))
    target_bytes = target.read_bytes()

    isolated = tmp_path / "download"
    nb = generate_workbench(script, isolated)
    (isolated / "target.png").unlink()
    text = nb.read_text()

    assert "TARGET_FILE" not in text
    assert base64.b64encode(target_bytes).decode("ascii") in text
    ast.parse(text)
