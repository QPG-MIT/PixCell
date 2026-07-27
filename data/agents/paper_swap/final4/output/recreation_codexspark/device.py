import json
import math
from pathlib import Path

import numpy as np
import gdsfactory as gf

# Top-level tunables (JEE-discoverable)
width_um = 0.66
end_gap_um = 1.68
min_gap_um = 0.29
delta_length_um = 0.0
device_length_um = 18.0
flat_length_um = 2.0
tail_length_um = 2.0
approach_length_um = 6.0
curve_samples = 64
layer = (1, 0)


def _cosine_segment(x0: float, x1: float, y0: float, y1: float, n: int) -> list[tuple[float, float]]:
    if n <= 1:
        return [(x1, y1)]
    pts = []
    for i in range(n):
        t = i / (n - 1)
        x = x0 + (x1 - x0) * t
        y = y0 + (y1 - y0) * 0.5 * (1.0 - math.cos(math.pi * t))
        pts.append((x, y))
    return pts


def _arm_points(top: bool, y_start: float, y_mid: float, total_length: float) -> list[tuple[float, float]]:
    if total_length <= 2 * tail_length_um + flat_length_um:
        raise ValueError("Invalid geometry: insufficient total_length for tails and flat section")

    x_tail_end = tail_length_um
    x_flat_start = x_tail_end + approach_length_um
    x_flat_end = total_length / 2 + flat_length_um / 2
    x_tail_start = total_length - tail_length_um

    if x_flat_end < x_flat_start or x_tail_start < x_flat_end:
        raise ValueError("Invalid geometry: adjust approach_length_um/flat_length_um/tail_length_um for this footprint")

    pts = []
    pts.append((0.0, y_start))
    pts.append((x_tail_end, y_start))
    pts.extend(_cosine_segment(x_tail_end, x_flat_start, y_start, y_mid, curve_samples))
    pts.append((x_flat_end, y_mid))
    pts.extend(_cosine_segment(x_flat_end, x_tail_start, y_mid, y_start, curve_samples))
    pts.append((total_length, y_start))

    if top:
        return pts

    # Bottom arm receives +delta_length_um by an intentional loop in x/y at the left edge.
    if delta_length_um <= 0.0:
        return pts

    d = delta_length_um / 4.0
    if d <= 0.0:
        return pts

    x0, y0 = pts[0]
    loop = [
        (x0, y0),
        (x0 + d, y0),
        (x0 + d, y0 + d),
        (x0, y0 + d),
        (x0, y0),
    ]
    # Deduplicate a shared vertex when stitching into baseline path
    return loop + pts[1:]


@gf.cell
def device() -> gf.Component:
    out_dir = Path(__file__).parent

    if not (min_gap_um > 0 and end_gap_um > min_gap_um):
        raise ValueError("Require end_gap_um > min_gap_um > 0")

    if not (curve_samples >= 4):
        raise ValueError("curve_samples must be >= 4")

    y_shift = (end_gap_um - min_gap_um) / 2.0
    top_y0 = 0.0
    top_ym = top_y0 + y_shift
    bot_y0 = width_um + end_gap_um
    bot_ym = bot_y0 - y_shift

    top_points = _arm_points(True, top_y0, top_ym, device_length_um)
    bot_points = _arm_points(False, bot_y0, bot_ym, device_length_um)

    top_path = gf.Path(np.array(top_points, dtype=float)).extrude(width=width_um, layer=layer)
    bot_path = gf.Path(np.array(bot_points, dtype=float)).extrude(width=width_um, layer=layer)

    c = gf.Component("recreation")
    c.add_ref(top_path)
    c.add_ref(bot_path)

    lengths = {
        "arms": {
            "top": float(gf.Path(np.array(top_points, dtype=float)).length()),
            "bottom": float(gf.Path(np.array(bot_points, dtype=float)).length()),
        },
        "delta_length_um": delta_length_um,
    }

    lengths["delta_length_um"] = lengths["arms"]["bottom"] - lengths["arms"]["top"]

    c.write_gds(out_dir / "device.gds")
    (out_dir / "lengths.json").write_text(json.dumps(lengths, indent=2))
    return c


if __name__ == "__main__":
    device()
