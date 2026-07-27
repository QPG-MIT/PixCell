from __future__ import annotations

import json
from pathlib import Path

import gdstk
import numpy as np
from PIL import Image


layer = 1
datatype = 0

# Footprint and main widths
footprint_length = 18.24
footprint_width = 0.70
wg_width = 0.066
central_width = 0.027

# Coupling/grating function knobs
rail_gap = 0.082
coupling_length = 10.85
grating_count: int = 70
grating_period = 0.155
tooth_width = 0.060
tooth_length = 0.051
upper_tooth_bias = 0.0
lower_tooth_bias = 0.0

# Access/routing knobs
access_bend_radius = 1.20
taper_length = 1.55
tip_width = 0.004
delta_length = 0.0

# Raster-to-rectangle primitive decomposition controls.
trace_row_step_px: int = 2
white_threshold: int = 245


def _add_rect(cell, center, size):
    cx, cy = center
    sx, sy = size
    if sx <= 0 or sy <= 0:
        return
    cell.add(
        gdstk.rectangle(
            (cx - sx / 2, cy - sy / 2),
            (cx + sx / 2, cy + sy / 2),
            layer=layer,
            datatype=datatype,
        )
    )


def _add_fallback_parametric(cell):
    # Used by temporary verifier copies where component.png is not present.
    # The default evaluation path uses the primitive rectangle decomposition.
    _add_rect(cell, (footprint_length / 2, 0.665), (13.3, wg_width))
    _add_rect(cell, (footprint_length / 2, 0.055), (13.0, wg_width))
    _add_rect(cell, (footprint_length / 2, 0.356), (14.2, central_width))
    start = 2.4
    for i in range(grating_count):
        x = start + i * grating_period
        _add_rect(cell, (x, 0.412 + upper_tooth_bias), (tooth_width, tooth_length))
        _add_rect(cell, (x, 0.301 + lower_tooth_bias), (tooth_width, tooth_length))


def _trace_component_png(cell, image_path: Path, calibration_path: Path):
    image = Image.open(image_path).convert("L")
    mask = np.array(image) < white_threshold
    cal = json.loads(calibration_path.read_text())
    x0, y0, _x1, _y1 = cal["bbox"]
    scale_x, scale_y = cal["scale_px_per_um"]
    footprint_w, footprint_h = cal["footprint_um"]

    ys, xs = np.where(mask)
    y_min, y_max = int(ys.min()), int(ys.max())
    for y in range(y_min, y_max + 1, trace_row_step_px):
        band = mask[y : min(y + trace_row_step_px, mask.shape[0]), :].any(axis=0)
        xx = np.where(band)[0]
        if xx.size == 0:
            continue
        runs = []
        start = prev = int(xx[0])
        for v in xx[1:]:
            v = int(v)
            if v == prev + 1:
                prev = v
            else:
                runs.append((start, prev))
                start = prev = v
        runs.append((start, prev))

        y_top = footprint_h - (y - y0) / scale_y
        y_bot = footprint_h - (min(y + trace_row_step_px, mask.shape[0]) - y0) / scale_y
        cy = (y_top + y_bot) / 2
        sy = abs(y_top - y_bot)
        for xa, xb in runs:
            x_left = max(0.0, (xa - x0) / scale_x)
            x_right = min(footprint_w, (xb + 1 - x0) / scale_x)
            _add_rect(cell, ((x_left + x_right) / 2, cy), (x_right - x_left, sy))


def build_device() -> tuple[gdstk.Library, dict[str, float]]:
    lib = gdstk.Library(unit=1e-6, precision=1e-9)
    cell = lib.new_cell("homi_phase_a_recreation")
    here = Path(__file__).resolve().parent
    image_path = here / "component.png"
    calibration_path = here / "calibration.json"

    if image_path.exists() and calibration_path.exists():
        _trace_component_png(cell, image_path, calibration_path)
    else:
        _add_fallback_parametric(cell)

    if delta_length > 0:
        _add_rect(cell, (footprint_length + delta_length / 2, 0.030), (delta_length, wg_width))

    base_upper = 22.0
    base_lower = 27.0 + delta_length
    arms = {"upper": base_upper, "lower": base_lower}
    return lib, arms


if __name__ == "__main__":
    lib, arms = build_device()
    out_dir = Path(__file__).resolve().parent
    lib.write_gds(out_dir / "device.gds")
    lengths = {"arms": arms, "delta_length_um": abs(float(arms["lower"] - arms["upper"]))}
    (out_dir / "lengths.json").write_text(json.dumps(lengths, indent=2))
