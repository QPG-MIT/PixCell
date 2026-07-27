from __future__ import annotations

import json
from pathlib import Path

import gdsfactory as gf
import numpy as np


# Top-level tunables, in microns.
footprint_length = 39.994
wg_width = 0.5
gap_um = 0.5
coupling_length = 18.80685086025288
sbend_length = 9.6
input_pitch = 3.5
delta_length = 0.001
npoints: int = 161
layer = (1, 0)


def _cosine_transition(x: np.ndarray, y0: float, y1: float, length: float) -> np.ndarray:
    t = np.clip(x / length, 0.0, 1.0)
    return y1 + (y0 - y1) * 0.5 * (1.0 + np.cos(np.pi * t))


def _centerline(sign: float, extra_length: float = 0.0) -> np.ndarray:
    y_outer = sign * input_pitch / 2.0
    y_coupled = sign * (wg_width + gap_um) / 2.0
    x1 = sbend_length
    x2 = sbend_length + coupling_length
    x3 = 2.0 * sbend_length + coupling_length

    left_x = np.linspace(0.0, x1, npoints)
    left_y = _cosine_transition(left_x, y_outer, y_coupled, sbend_length)

    mid_x = np.linspace(x1, x2, max(2, npoints // 2))
    mid_y = np.full_like(mid_x, y_coupled)

    right_x = np.linspace(x2, x3, npoints)
    right_y = _cosine_transition(right_x - x2, y_coupled, y_outer, sbend_length)

    x = np.concatenate([left_x, mid_x[1:], right_x[1:]])
    y = np.concatenate([left_y, mid_y[1:], right_y[1:]])

    nominal_end = footprint_length
    if x3 < nominal_end:
        tail_x = np.linspace(x3, nominal_end, max(2, npoints // 4))
        tail_y = np.full_like(tail_x, y_outer)
        x = np.concatenate([x, tail_x[1:]])
        y = np.concatenate([y, tail_y[1:]])

    if extra_length > 0:
        trim_x = np.linspace(nominal_end, nominal_end + extra_length, max(2, npoints // 8))
        trim_y = np.full_like(trim_x, y_outer)
        x = np.concatenate([x, trim_x[1:]])
        y = np.concatenate([y, trim_y[1:]])

    return np.column_stack([x, y])


def _polyline_length(points: np.ndarray) -> float:
    return float(np.sum(np.linalg.norm(np.diff(points, axis=0), axis=1)))


@gf.cell
def build_device() -> gf.Component:
    c = gf.Component()

    top_points = _centerline(+1.0, extra_length=delta_length)
    bottom_points = _centerline(-1.0, extra_length=0.0)

    for points in (top_points, bottom_points):
        path = gf.Path(points)
        guide = gf.path.extrude(path, width=wg_width, layer=layer)
        c << guide

    c.add_label("directional_coupler_primitives_only", position=(1.0, 0.0), layer=layer)
    return c


def main() -> None:
    gf.clear_cache()
    component = build_device().copy()
    component.flatten()
    out_dir = Path(__file__).resolve().parent
    gds_path = out_dir / "device.gds"
    component.write_gds(gds_path, with_metadata=False)

    top_points = _centerline(+1.0, extra_length=delta_length)
    bottom_points = _centerline(-1.0, extra_length=0.0)
    arms = {
        "top": _polyline_length(top_points),
        "bottom": _polyline_length(bottom_points),
    }
    payload = {
        "arms": arms,
        "delta_length_um": abs(arms["top"] - arms["bottom"]),
        "coupler": {
            "length_um": coupling_length,
            "gap_um": gap_um,
            "width_um": wg_width,
        },
    }
    (out_dir / "lengths.json").write_text(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
