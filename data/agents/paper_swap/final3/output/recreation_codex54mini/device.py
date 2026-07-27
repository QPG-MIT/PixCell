from __future__ import annotations

import json
from pathlib import Path

import gdsfactory as gf

LAYER = (1, 0)

footprint_length_um = 120.0
footprint_width_um = 4.0

# Real tunables exposed at module scope for JEE-style substitution.
wg_width_um = 0.34
lead_length_um = 15.0
transition_length_um = 17.5
center_length_um = 54.5
bend_radius_um = 5.0
delta_length = 0.0

top_start_y_um = 0.28
top_mid_y_um = 1.78
bottom_mid_y_um = 2.22
bottom_start_y_um = 3.72


def _smooth_route(y_start: float, y_mid: float, *, extra_center_um: float = 0.0) -> gf.Path:
    """Build one routed arm as a smooth S-bend with a long center straight."""
    end_x = footprint_length_um + extra_center_um
    points = [
        (0.0, y_start),
        (lead_length_um, y_start),
        (lead_length_um + transition_length_um, y_mid),
        (lead_length_um + transition_length_um + center_length_um, y_mid),
        (end_x - lead_length_um, y_start),
        (end_x, y_start),
    ]
    return gf.path.smooth(points, radius=bend_radius_um, bend=gf.path.euler)


def device() -> gf.Component:
    c = gf.Component("device")

    upper = _smooth_route(top_start_y_um, top_mid_y_um, extra_center_um=delta_length)
    lower = _smooth_route(bottom_start_y_um, bottom_mid_y_um, extra_center_um=0.0)

    c << gf.path.extrude(upper, width=wg_width_um, layer=LAYER)
    c << gf.path.extrude(lower, width=wg_width_um, layer=LAYER)

    return c


def _write_lengths(out_dir: Path) -> None:
    upper = _smooth_route(top_start_y_um, top_mid_y_um, extra_center_um=delta_length)
    lower = _smooth_route(bottom_start_y_um, bottom_mid_y_um, extra_center_um=0.0)
    payload = {
        "arms": {
            "upper": float(upper.length()),
            "lower": float(lower.length()),
        },
        "delta_length_um": float(abs(upper.length() - lower.length())),
    }
    (out_dir / "lengths.json").write_text(json.dumps(payload, indent=2))


if __name__ == "__main__":
    out_dir = Path(__file__).resolve().parent
    component = device()
    gds_path = out_dir / "device.gds"
    component.write_gds(gds_path, with_metadata=False)
    _write_lengths(out_dir)
