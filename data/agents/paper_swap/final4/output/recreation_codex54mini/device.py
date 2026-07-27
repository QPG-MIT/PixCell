from __future__ import annotations

import json
from pathlib import Path

import gdsfactory as gf
import numpy as np


layer = (1, 0)
length_um = 18.0
footprint_width_um = 3.0
wg_width_um = 0.662
upper_gap_edge_um = 2.346
lower_gap_edge_um = 2.339
gap_mid_um = 0.944
delta_length = 0.0


def centerline_gap(x_um: np.ndarray, edge_gap_um: float) -> np.ndarray:
    """Center-to-center gap profile, wide at the ends and narrow in the middle."""
    phase = np.cos(np.pi * x_um / length_um) ** 2
    return gap_mid_um + (edge_gap_um - gap_mid_um) * phase


def arm_points(arm: str) -> list[tuple[float, float]]:
    x = np.linspace(0.0, length_um, 401)
    edge_gap_um = upper_gap_edge_um if arm == "upper" else lower_gap_edge_um
    gap = centerline_gap(x, edge_gap_um)
    mid_y = footprint_width_um / 2.0
    if arm == "upper":
        y = mid_y - gap / 2.0
    elif arm == "lower":
        y = mid_y + gap / 2.0
    else:
        raise ValueError(f"Unknown arm '{arm}'")
    return list(zip(x.tolist(), y.tolist()))


def arm_length(points: list[tuple[float, float]]) -> float:
    return gf.Path(points).length()


@gf.cell
def build_device() -> gf.Component:
    c = gf.Component()

    upper_path = gf.Path(arm_points("upper"))
    lower_path = gf.Path(arm_points("lower"))

    upper_end_y = arm_points("upper")[-1][1]
    c.add_ref(gf.path.extrude(upper_path, width=wg_width_um, layer=layer))
    if delta_length != 0.0:
        tail = gf.components.rectangle(size=(delta_length, wg_width_um), layer=layer, centered=False)
        c.add_ref(tail).move((length_um, upper_end_y - wg_width_um / 2.0))
    c.add_ref(gf.path.extrude(lower_path, width=wg_width_um, layer=layer))

    lengths = {
        "arms": {
            "upper": arm_length(arm_points("upper")) + max(delta_length, 0.0),
            "lower": arm_length(arm_points("lower")),
        },
        "delta_length_um": max(delta_length, 0.0),
    }
    Path(__file__).with_name("lengths.json").write_text(json.dumps(lengths, indent=2))
    return c


def main() -> None:
    out = Path(__file__).with_suffix(".gds")
    comp = build_device()
    comp.write_gds(out, with_metadata=False)
    print(out)


if __name__ == "__main__":
    main()
