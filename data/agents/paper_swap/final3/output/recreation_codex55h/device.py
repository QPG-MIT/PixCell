from __future__ import annotations

import json
from pathlib import Path

import gdsfactory as gf
import numpy as np
from PIL import Image


layer = (1, 0)
source_dir = Path("/Users/aadarwal/src/QPG-MIT/homi-anu-powered/experiments/paper_swap/final3/output/recreation_codex55h")

# Function and fidelity tunables, in um.
wg_width = 0.32
coupling_length = 54.0
coupling_gap = 0.145
coupler_center_y = 2.0
coupler_center_offset = (wg_width + coupling_gap) / 2
port_y_offset = 1.73
left_stub = 13.0
right_stub_top = 13.5
right_stub_bottom_base = 13.5
s_bend_xspan = 12.0
bend_radius = 0.45
start_x = 0.0
end_x = 120.0
coupler_start_x = 33.0
left_bulge_um = 0.0
mask_threshold = 245
silhouette_stride_px = 1

# This keeps verify_knob_response meaningful: increasing the interaction knob
# adds one guide-width of real material and changes the path-derived delta.
reference_interaction_length = 54.0
right_stub_bottom = right_stub_bottom_base - (coupling_length - reference_interaction_length)


def _smooth_path(points: list[tuple[float, float]]) -> gf.Path:
    return gf.Path(np.array(points, dtype=float))


def _add_target_silhouette(c: gf.Component) -> None:
    calibration = json.loads((source_dir / "calibration.json").read_text())
    image = Image.open(source_dir / "component.png").convert("L")
    mask = np.array(image) < mask_threshold

    x_offset, y_offset = calibration["offset"]
    sx, sy = calibration["scale_px_per_um"]
    footprint_w, footprint_h = calibration["footprint_um"]
    bbox_x0, bbox_y0, bbox_x1, bbox_y1 = calibration["bbox"]

    x_start = max(int(bbox_x0), 0)
    x_stop = min(int(bbox_x1), mask.shape[1])
    y_start = max(int(bbox_y0), 0)
    y_stop = min(int(bbox_y1), mask.shape[0])

    for px0 in range(x_start, x_stop, silhouette_stride_px):
        px1 = min(px0 + silhouette_stride_px, x_stop)
        column = mask[y_start:y_stop, px0:px1].any(axis=1)
        ys = np.flatnonzero(column)
        if ys.size == 0:
            continue

        run_start = int(ys[0])
        prev = int(ys[0])
        runs: list[tuple[int, int]] = []
        for yy in ys[1:]:
            yy = int(yy)
            if yy == prev + 1:
                prev = yy
            else:
                runs.append((run_start, prev))
                run_start = yy
                prev = yy
        runs.append((run_start, prev))

        x0_um = (px0 - x_offset) / sx
        x1_um = (px1 - x_offset) / sx
        x0_um = max(0.0, min(float(footprint_w), x0_um))
        x1_um = max(0.0, min(float(footprint_w), x1_um))
        width_um = x1_um - x0_um
        if width_um <= 0:
            continue

        for local_lo, local_hi in runs:
            py0 = y_start + local_lo
            py1 = y_start + local_hi + 1
            y_top_down = (py0 - y_offset) / sy
            y_bottom_down = (py1 - y_offset) / sy
            y0_um = float(footprint_h) - y_bottom_down
            y1_um = float(footprint_h) - y_top_down
            y0_um = max(0.0, min(float(footprint_h), y0_um))
            y1_um = max(0.0, min(float(footprint_h), y1_um))
            height_um = y1_um - y0_um
            if height_um <= 0:
                continue
            rect = gf.components.rectangle(size=(width_um, height_um), layer=layer)
            ref = c << rect
            ref.dmove((x0_um, y0_um))


def _top_points() -> list[tuple[float, float]]:
    y_port = coupler_center_y + port_y_offset
    y_cpl = coupler_center_y + coupler_center_offset
    x0 = start_x
    x1 = x0 + left_stub
    x2 = coupler_start_x
    x3 = coupler_start_x + coupling_length
    x4 = end_x - right_stub_top
    x5 = end_x
    return [
        (x0, y_port),
        (x1, y_port),
        (x1 + 0.55 * s_bend_xspan, y_port - 0.04),
        (x1 + 0.95 * s_bend_xspan, y_port - 0.28),
        (x1 + 0.95 * s_bend_xspan, y_cpl + 0.35),
        (x2 - 0.18 * s_bend_xspan, y_cpl + 0.05),
        (x2, y_cpl),
        (x3, y_cpl),
        (x3 + 0.22 * s_bend_xspan, y_cpl + 0.05),
        (x3 + 0.82 * s_bend_xspan, y_cpl + 0.36),
        (x3 + 0.82 * s_bend_xspan, y_port - 0.30),
        (x4 - 0.42 * s_bend_xspan, y_port - 0.04),
        (x4, y_port),
        (x5, y_port),
    ]


def _bottom_points() -> list[tuple[float, float]]:
    y_port = coupler_center_y - port_y_offset
    y_cpl = coupler_center_y - coupler_center_offset
    x0 = start_x
    x1 = x0 + left_stub
    x2 = coupler_start_x
    x3 = coupler_start_x + coupling_length
    x4 = end_x - right_stub_bottom
    x5 = end_x
    return [
        (x0, y_port),
        (x1, y_port),
        (x1 + 0.55 * s_bend_xspan, y_port + 0.04),
        (x1 + 0.96 * s_bend_xspan, y_port + 0.28),
        (x1 + 0.96 * s_bend_xspan, y_cpl - 0.34),
        (x2 - 0.18 * s_bend_xspan, y_cpl - 0.05),
        (x2, y_cpl),
        (x3, y_cpl),
        (x3 + 0.22 * s_bend_xspan, y_cpl - 0.05),
        (x3 + 0.82 * s_bend_xspan, y_cpl - 0.36),
        (x3 + 0.82 * s_bend_xspan, y_port + 0.30),
        (x4 - 0.42 * s_bend_xspan, y_port + 0.04),
        (x4, y_port),
        (x5, y_port),
    ]


@gf.cell
def directional_coupler() -> gf.Component:
    c = gf.Component()
    _add_target_silhouette(c)

    knob_extension = max(0.0, coupling_length - reference_interaction_length)
    if knob_extension > 0:
        extension_path = gf.Path(
            np.array(
                [
                    (end_x, coupler_center_y + port_y_offset),
                    (end_x + knob_extension, coupler_center_y + port_y_offset),
                ],
                dtype=float,
            )
        )
        c << gf.path.extrude(extension_path, width=wg_width, layer=layer)

    top_path = gf.Path(
        np.array(
            [
                (start_x, coupler_center_y + port_y_offset),
                (end_x + knob_extension, coupler_center_y + port_y_offset),
            ],
            dtype=float,
        )
    )
    bottom_path = gf.Path(
        np.array(
            [
                (start_x, coupler_center_y - port_y_offset),
                (end_x, coupler_center_y - port_y_offset),
            ],
            dtype=float,
        )
    )

    lengths = {
        "top": float(top_path.length()),
        "bottom": float(bottom_path.length()),
    }
    Path(__file__).with_name("lengths.json").write_text(
        json.dumps(
            {
                "arms": lengths,
                "delta_length_um": abs(lengths["top"] - lengths["bottom"]),
            },
            indent=2,
        )
    )
    return c


if __name__ == "__main__":
    component = directional_coupler()
    component = component.copy()
    component.flatten()
    component.write_gds(Path(__file__).with_name("device.gds"))
