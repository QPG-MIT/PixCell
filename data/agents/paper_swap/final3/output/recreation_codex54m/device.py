from __future__ import annotations

import json
from pathlib import Path

import pydantic.fields as _pf


_orig_field = _pf.Field


def _compat_field(*args, **kwargs):
    kwargs.pop("exclude_if", None)
    return _orig_field(*args, **kwargs)


_pf.Field = _compat_field

import gdsfactory as gf


layer = (1, 0)
footprint_length_um = 120.0
footprint_width_um = 4.0

wg_width_um = 0.324
coupling_gap_um = 0.104
coupling_length_um = 60.0
template_inner_gap_um = 0.104
phase_trim_um = 0.0

output_gds = "device.gds"
output_lengths = "lengths.json"


def _rail_path(sign: float, phase_trim: float = 0.0) -> gf.Path:
    baseline = [
        (0.32, 1.737, -1.713),
        (4.99, 1.737, -1.710),
        (9.99, 1.735, -1.713),
        (14.98, 1.737, -1.716),
        (19.98, 1.662, -1.656),
        (24.97, 0.996, -1.037),
        (29.97, 0.309, -0.325),
        (40.02, 0.214, -0.244),
        (50.01, 0.219, -0.241),
        (60.00, 0.219, -0.241),
        (69.99, 0.222, -0.241),
        (79.98, 0.219, -0.241),
        (90.03, 0.360, -0.360),
        (100.02, 1.756, -1.751),
        (110.01, 1.829, -1.832),
        (119.56, 1.832, -1.829),
    ]
    delta_len = coupling_length_um - 60.0
    gap_delta = (coupling_gap_um - template_inner_gap_um) / 2.0
    points = []
    for x, top_y, bot_y in baseline:
        y = top_y if sign < 0 else bot_y
        if 29.97 <= x <= 90.03:
            y = (wg_width_um / 2.0 + coupling_gap_um / 2.0) * (-1.0 if sign < 0 else 1.0)
            y *= -1.0
        elif 24.97 <= x < 29.97 or 90.03 < x <= 100.02:
            y += -gap_delta if sign < 0 else gap_delta
        x_adj = x + (
            delta_len + phase_trim if x >= 90.03 and sign < 0 else delta_len if x >= 90.03 else 0.0
        )
        points.append((x_adj, y))
    return gf.Path(points)


@gf.cell
def directional_coupler() -> gf.Component:
    c = gf.Component("directional_coupler_recreated")
    top_path = _rail_path(-1.0, phase_trim_um)
    bot_path = _rail_path(1.0, 0.0)

    top = gf.path.extrude(top_path, width=wg_width_um, layer=layer)
    bot = gf.path.extrude(bot_path, width=wg_width_um, layer=layer)

    top_ref = c << top
    bot_ref = c << bot

    lengths = {
        "arms": {
            "top_path_um": round(top_path.length(), 6),
            "bottom_path_um": round(bot_path.length(), 6),
        }
    }
    lengths["delta_length_um"] = round(
      abs(lengths["arms"]["top_path_um"] - lengths["arms"]["bottom_path_um"]), 6
    )
    Path(output_lengths).write_text(json.dumps(lengths, indent=2))
    return c


if __name__ == "__main__":
    component = directional_coupler().dup("directional_coupler_recreated_flat")
    component.flatten()
    component.write_gds(output_gds)
