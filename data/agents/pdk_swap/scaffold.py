"""Scaffold the PDK-swap experiment inputs.

Renders the input MZI image (the 'paper figure' the worker recreates — it never
learns the source), writes footprint/spec/stack definitions.

Run from the repo root:  .venv/bin/python data/agents/pdk_swap/scaffold.py
Spec: docs/superpowers/specs/2026-07-02-pdk-swap-spec-optimization-design.md
"""
import json
from pathlib import Path

import gdsfactory as gf
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).parent

# --- the baseline device, exactly as pictured -------------------------------
BASELINE_DELTA_LENGTH = 10.0  # gdsfactory default, the geometry in the image
component = gf.components.mzi(delta_length=BASELINE_DELTA_LENGTH)

xmin, ymin = component.xmin, component.ymin
xmax, ymax = component.xmax, component.ymax
length_um = round(xmax - xmin, 2)
width_um = round(ymax - ymin, 2)

# --- render device-only B&W image (black material on white, layer (1,0)) ----
# gf 9.20.7 keys the merged dict by layer index (1 == layer (1,0))
poly_dict = component.copy().get_polygons_points(merge=True)
polys = poly_dict.get(1) or poly_dict.get((1, 0)) or []
PX_PER_UM = 8
fig, ax = plt.subplots(
    figsize=(length_um * PX_PER_UM / 100, width_um * PX_PER_UM / 100), dpi=100
)
for p in polys:
    ax.fill(p[:, 0], p[:, 1], color="black", linewidth=0)
ax.set_xlim(xmin, xmax)
ax.set_ylim(ymin, ymax)
ax.set_aspect("equal")
ax.axis("off")
fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
fig.savefig(HERE / "mzi_input.png", facecolor="white")
plt.close(fig)

from PIL import Image  # noqa: E402

Image.open(HERE / "mzi_input.png").convert("L").save(HERE / "mzi_input.png")

(HERE / "footprint.json").write_text(
    json.dumps({"footprint_um": [length_um, width_um]}, indent=2)
)

# --- the spec ----------------------------------------------------------------
spec = {
    "device": "mzi",
    "target": {"metric": "fsr_nm", "value": 8.0, "tolerance_rel": 0.02},
    "wavelength_um": 1.55,
    "mode": "TE0",
    "note": "FSR = lambda^2 / (n_g * delta_L); n_g from local mode solve per stack",
}
(HERE / "spec.json").write_text(json.dumps(spec, indent=2))

# --- three layer stacks, grounded in the repo's own tables --------------------
stacks = {
    "soi220": {
        "label": "220 nm SOI strip",
        "source": "gg/servers/pdk_server.py AVAILABLE_PDKS['generic_si220']",
        "core_material": "Si",
        "core_n": 3.476,
        "clad_material": "SiO2",
        "clad_n": 1.444,
        "thickness_um": 0.220,
        "single_mode_width_um": 0.500,
        "min_feature_um": 0.18,
    },
    "sin400": {
        "label": "400 nm SiN strip",
        "source": "gg/servers/pdk_server.py AVAILABLE_PDKS['sin']",
        "core_material": "SiN",
        "core_n": 1.996,
        "clad_material": "SiO2",
        "clad_n": 1.444,
        "thickness_um": 0.400,
        "single_mode_width_um": 1.000,
        "min_feature_um": 0.40,
    },
    "tfln400": {
        "label": "400 nm TFLN strip (isotropic approx)",
        "source": "Flex/core/materials.py MATERIAL_PRESETS['Lithium Niobate'] (n_e)",
        "core_material": "LiNbO3",
        "core_n": 2.138,
        "clad_material": "SiO2",
        "clad_n": 1.444,
        "thickness_um": 0.400,
        "single_mode_width_um": 1.200,
        "min_feature_um": 0.50,
    },
}
stacks_dir = HERE / "stacks"
stacks_dir.mkdir(exist_ok=True)
for name, s in stacks.items():
    (stacks_dir / f"{name}.json").write_text(json.dumps(s, indent=2))

# --- keep the baseline geometry for later verification ------------------------
out = HERE / "baseline"
out.mkdir(exist_ok=True)
component.write_gds(out / "mzi_baseline.gds")
(out / "baseline_params.json").write_text(
    json.dumps(
        {
            "generator": "gf.components.mzi (worker is blind to this)",
            "delta_length_um": BASELINE_DELTA_LENGTH,
            "bbox_um": [length_um, width_um],
        },
        indent=2,
    )
)

print(f"MZI bbox: {length_um} x {width_um} um, {len(polys)} polygons")
print(f"wrote: mzi_input.png, footprint.json, spec.json, stacks/*.json, baseline/")
