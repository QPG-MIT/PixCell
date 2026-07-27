from __future__ import annotations

import json
from pathlib import Path

import gdsfactory as gf
import numpy as np


footprint_length_um = 18.0
footprint_width_um = 3.0
wg_width_um = 0.6544
port_sep_um = 2.3491
coupling_gap_um = 0.3231
coupling_length_um = 1.5762
transition_length_um = 7.9394
lead_length_um = 0.2725
delta_length_um = 0.0
samples_per_transition = 160
layer_num = 1
datatype_num = 0


def _smoothstep(t: np.ndarray) -> np.ndarray:
    return t * t * t * (10 + t * (-15 + 6 * t))


def _offset_profile(x: np.ndarray, *, coupling_length: float) -> np.ndarray:
    port_offset = port_sep_um / 2
    coupled_offset = (wg_width_um + coupling_gap_um) / 2
    x1 = lead_length_um
    x2 = x1 + transition_length_um
    x3 = x2 + coupling_length
    x4 = x3 + transition_length_um

    y = np.empty_like(x, dtype=float)
    y[x <= x1] = port_offset

    m = (x > x1) & (x <= x2)
    y[m] = port_offset + (coupled_offset - port_offset) * _smoothstep(
        (x[m] - x1) / transition_length_um
    )

    m = (x > x2) & (x <= x3)
    y[m] = coupled_offset

    m = (x > x3) & (x <= x4)
    y[m] = coupled_offset + (port_offset - coupled_offset) * _smoothstep(
        (x[m] - x3) / transition_length_um
    )

    y[x > x4] = port_offset
    return y


def _centerline(sign: float, *, extra_length: float = 0.0) -> np.ndarray:
    base_length = 2 * lead_length_um + 2 * transition_length_um + coupling_length_um
    n = max(48, int(2 * samples_per_transition + coupling_length_um * 30))
    x = np.linspace(0.0, base_length, n)
    offset = _offset_profile(x, coupling_length=coupling_length_um)
    y = footprint_width_um / 2 + sign * offset
    points = np.column_stack([x, y])
    if extra_length:
        points = np.vstack([points, [base_length + extra_length, y[-1]]])
    return points


def _path_length(points: np.ndarray) -> float:
    diffs = np.diff(points, axis=0)
    return float(np.sum(np.hypot(diffs[:, 0], diffs[:, 1])))


@gf.cell
def device() -> gf.Component:
    c = gf.Component()
    layer = (layer_num, datatype_num)

    top_points = _centerline(+1.0, extra_length=delta_length_um)
    bottom_points = _centerline(-1.0)

    top = gf.path.extrude(gf.Path(top_points), width=wg_width_um, layer=layer)
    bottom = gf.path.extrude(gf.Path(bottom_points), width=wg_width_um, layer=layer)
    c.add_ref(top)
    c.add_ref(bottom)

    c.info["top_length_um"] = _path_length(top_points)
    c.info["bottom_length_um"] = _path_length(bottom_points)
    return c


if __name__ == "__main__":
    out_dir = Path(__file__).resolve().parent
    component = device().copy()
    component.flatten()
    top_length = float(component.info["top_length_um"])
    bottom_length = float(component.info["bottom_length_um"])
    with open(out_dir / "lengths.json", "w") as f:
        json.dump(
            {
                "arms": {
                    "top": top_length,
                    "bottom": bottom_length,
                },
                "delta_length_um": top_length - bottom_length,
            },
            f,
            indent=2,
        )
    component.write_gds(out_dir / "device.gds", with_metadata=False)
