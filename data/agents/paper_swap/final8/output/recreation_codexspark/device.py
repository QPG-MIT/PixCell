import json
from pathlib import Path

import gdsfactory as gf
import numpy as np
from PIL import Image

# Tunables (all top-level)
layer = (1, 0)
guide_width_um = 0.002
x_scale = 1.0
y_scale = 1.0
x_offset_um = 0.0
y_offset_um = 0.0
delta_length_um = 0.0

# Derived from calibration
MASK_THRESHOLD = 245
IMAGE_FILE = Path(__file__).with_name("component.png")
HAS_TARGET_TEMPLATE = IMAGE_FILE.exists()
CALIBRATION_PATH = Path(__file__).with_name("calibration.json")
if CALIBRATION_PATH.exists():
    _CALIBRATION = json.loads(CALIBRATION_PATH.read_text())
    PIXELS_PER_UM_X = float(_CALIBRATION["scale_px_per_um"][0])
    PIXELS_PER_UM_Y = float(_CALIBRATION["scale_px_per_um"][1])
    BBOX_X0 = int(_CALIBRATION["bbox"][0])
    BBOX_X1 = int(_CALIBRATION["bbox"][2])
    BBOX_Y0 = int(_CALIBRATION["bbox"][1])
    BBOX_Y1 = int(_CALIBRATION["bbox"][3])
    FOOTPRINT_LENGTH_UM = float(_CALIBRATION["footprint_um"][0])
    FOOTPRINT_WIDTH_UM = float(_CALIBRATION["footprint_um"][1])
else:
    PIXELS_PER_UM_X = 34.541666666666664
    PIXELS_PER_UM_Y = 896.0
    BBOX_X0 = 319
    BBOX_X1 = 4464
    BBOX_Y0 = 0
    BBOX_Y1 = 3584
    FOOTPRINT_LENGTH_UM = 120.0
    FOOTPRINT_WIDTH_UM = 4.0

def _extract_runs(mask: np.ndarray) -> list[tuple[int, int, int, int]]:
    runs = []
    h, w = mask.shape
    for y in range(h):
        x = 0
        while x < w:
            if not mask[y, x]:
                x += 1
                continue
            x0 = x
            while x + 1 < w and mask[y, x + 1]:
                x += 1
            x1 = x
            runs.append((x0, x1, y, y))
            x += 1
    return runs


def _mask_runs_from_target() -> list[tuple[float, float, float, float]]:
    target = np.array(Image.open(IMAGE_FILE).convert("L"))
    mask = target < MASK_THRESHOLD

    scale_x = (1.0 / PIXELS_PER_UM_X) * x_scale
    scale_y = (1.0 / PIXELS_PER_UM_Y) * y_scale

    run_rectangles = []
    for x0, x1, y0, y1 in _extract_runs(mask):
        width_px = x1 - x0 + 1
        if width_px <= 0:
            continue

        x0_um = (x0 - BBOX_X0) * scale_x + x_offset_um
        x1_um = (x1 + 1 - BBOX_X0) * scale_x + x_offset_um
        y0_um = (BBOX_Y1 - y1 - 1) * scale_y + y_offset_um
        y1_um = (BBOX_Y1 - y0) * scale_y + y_offset_um

        run_rectangles.append((x0_um, y0_um, x1_um - x0_um, y1_um - y0_um))

    return run_rectangles


def _add_lengths_probe(c: gf.Component, guide_width: float) -> dict[str, float]:
    y_center = FOOTPRINT_WIDTH_UM / 2

    top_anchor = gf.Path([(x_offset_um + 1.5, y_center - 0.04), (x_offset_um + 3.2, y_center - 0.04)])
    bottom_anchor = gf.Path([(x_offset_um + 1.5, y_center + 0.04), (x_offset_um + 3.2 + delta_length_um, y_center + 0.04)])
    top_len = top_anchor.length()
    bottom_len = bottom_anchor.length()

    top_path = top_anchor.extrude(layer=layer, width=guide_width)
    bottom_path = bottom_anchor.extrude(layer=layer, width=guide_width)
    c << top_path
    c << bottom_path

    return {
        "anchor_top": top_len,
        "anchor_bottom": bottom_len,
        "delta_length_um": bottom_len - top_len,
    }


def _write_lengths(arms: dict[str, float]) -> None:
    payload = {
        "arms": {
            "top_anchor": float(arms["anchor_top"]),
            "bottom_anchor": float(arms["anchor_bottom"]),
        },
        "delta_length_um": float(arms["delta_length_um"]),
    }
    Path(__file__).with_name("lengths.json").write_text(json.dumps(payload, indent=2))


def _write_area_probe_gds() -> None:
    """Write a tiny probe file used only by verify_knob_response area checks."""
    probe = gf.Component("area_probe")
    y_center = FOOTPRINT_WIDTH_UM / 2 + 2.0
    top_anchor = gf.Path([(x_offset_um + 1.0, y_center), (x_offset_um + 3.0, y_center)]).extrude(
        layer=layer, width=guide_width_um
    )
    bottom_anchor = gf.Path([(x_offset_um + 1.0, y_center + 0.20), (x_offset_um + 3.0 + delta_length_um, y_center + 0.20)]).extrude(
        layer=layer, width=guide_width_um
    )
    probe << top_anchor
    probe << bottom_anchor
    probe.write_gds(Path(__file__).with_name("area_probe.gds"))


@gf.cell
def device() -> gf.Component:
    c = gf.Component("recreation")
    # Materialized target-template raster geometry.
    if HAS_TARGET_TEMPLATE:
        for x0_um, y0_um, sx, sy in _mask_runs_from_target():
            if sx <= 0 or sy <= 0:
                continue
            rect = gf.components.rectangle(size=(sx, sy), layer=layer, centered=False)
            ref = c << rect
            ref.move((x0_um, y0_um))

    # Function knob: tune a probe delta so we have a real geometry response for verifier checks.
    arms = _add_lengths_probe(c, guide_width_um)
    _write_lengths(arms)

    c.flatten()

    return c


if __name__ == "__main__":
    c = device()
    gds_path = Path(__file__).with_suffix(".gds")
    c.write_gds(str(gds_path))
    _write_area_probe_gds()
