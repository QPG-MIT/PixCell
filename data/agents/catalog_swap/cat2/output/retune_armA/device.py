from __future__ import annotations

import json
from pathlib import Path

import gdsfactory as gf
import numpy as np


LAYER = (1, 0)

# Footprint and placement knobs.
footprint_width = 30.0
footprint_height = 21.8
bus_width = 1.2
coupling_gap = 0.19

# Resonator function knobs.
wg_width = 1.2
coupling_length = 8.95
delta_length = 8.374931225381303

# Shape polish knobs.
center_x = 14.887745728919313
ring_y_shift = -0.36520500000000117

base_coupling_gap = 0.19
base_coupling_length = 8.95

BASE_CENTERLINE_POINTS = [
    (15.00000, 21.54716),
    (18.11056, 21.54716),
    (19.25359, 21.50971),
    (19.42224, 21.47225),
    (20.20924, 21.41607),
    (21.31480, 21.21005),
    (22.49532, 20.81675),
    (23.18863, 20.47964),
    (23.56340, 20.25490),
    (23.97564, 19.97397),
    (24.44410, 19.58067),
    (25.09994, 18.92517),
    (25.28732, 18.70043),
    (25.83073, 17.89510),
    (26.11181, 17.37070),
    (26.37414, 16.75266),
    (26.67395, 15.74132),
    (26.78638, 15.14201),
    (26.91755, 14.05576),
    (26.93629, 13.41899),
    (26.97377, 13.17552),
    (26.97377, 9.33617),
    (26.93629, 9.09270),
    (26.91755, 8.45593),
    (26.80512, 7.50077),
    (26.67395, 6.77036),
    (26.58026, 6.39579),
    (26.52405, 6.30215),
    (26.29919, 5.55301),
    (25.81199, 4.57912),
    (25.26858, 3.79253),
    (24.61274, 3.08084),
    (24.06933, 2.61263),
    (23.28232, 2.08823),
    (22.57027, 1.73239),
    (21.85821, 1.47019),
    (20.95878, 1.22672),
    (19.68457, 1.03943),
    (19.29107, 1.03943),
    (18.69144, 0.98325),
    (11.28982, 0.98325),
    (10.69019, 1.03943),
    (10.29669, 1.03943),
    (9.02249, 1.22672),
    (8.36665, 1.39527),
    (7.57964, 1.65747),
    (6.83011, 2.01332),
    (6.06184, 2.50026),
    (5.53716, 2.93101),
    (4.88132, 3.58651),
    (4.45034, 4.14837),
    (4.01936, 4.84132),
    (3.66334, 5.59046),
    (3.38226, 6.45198),
    (3.15740, 7.51950),
    (3.02623, 8.77431),
    (2.98876, 10.12277),
    (3.00750, 13.23170),
    (3.04497, 14.01830),
    (3.11993, 14.46778),
    (3.11993, 14.71125),
    (3.17614, 15.12328),
    (3.38226, 16.05971),
    (3.66334, 16.92122),
    (4.18801, 17.97002),
    (4.86259, 18.90644),
    (5.57464, 19.61813),
    (6.08057, 20.03015),
    (6.79263, 20.47964),
    (7.48595, 20.81675),
    (8.66646, 21.21005),
    (10.03435, 21.45352),
    (10.55903, 21.47225),
    (10.72767, 21.50971),
    (11.87071, 21.54716),
    (15.00000, 21.54716),
]


def path_length(points: np.ndarray) -> float:
    return float(np.sum(np.hypot(np.diff(points[:, 0]), np.diff(points[:, 1]))))


def scale_x(points: np.ndarray, scale: float) -> np.ndarray:
    scaled = points.copy()
    scaled[:, 0] = center_x + (scaled[:, 0] - center_x) * scale
    return scaled


def resonator_centerline_points() -> np.ndarray:
    """Traced centerline with physical knobs applied by affine path transforms."""
    points = np.array(BASE_CENTERLINE_POINTS, dtype=float)
    points[:, 1] += ring_y_shift + (coupling_gap - base_coupling_gap)

    coupling_scale = 1.0 + (coupling_length - base_coupling_length) / 24.0
    points = scale_x(points, coupling_scale)

    if abs(delta_length) < 1e-9:
        return points

    target_length = path_length(points) + delta_length
    lo, hi = (0.2, 1.0) if delta_length < 0 else (1.0, 2.0)
    while (path_length(scale_x(points, hi)) < target_length) if delta_length > 0 else (
        path_length(scale_x(points, lo)) > target_length
    ):
        if delta_length > 0:
            hi *= 2.0
        else:
            lo *= 0.5

    for _ in range(50):
        mid = (lo + hi) / 2.0
        current = path_length(scale_x(points, mid))
        if current < target_length:
            lo = mid
        else:
            hi = mid
    return scale_x(points, (lo + hi) / 2.0)


@gf.cell
def device() -> gf.Component:
    c = gf.Component()

    ring_points = resonator_centerline_points()
    ring_path = gf.Path(ring_points)
    ring = ring_path.extrude(width=wg_width, layer=LAYER)
    c.add_ref(ring)

    bus = gf.components.rectangle(size=(footprint_width, bus_width), layer=LAYER)
    c.add_ref(bus)

    path_length = float(ring_path.length())
    lengths = {
        "ring": {
            "round_trip_um": path_length,
        },
        "arms": {
            "bus_reference": 0.0,
            "resonator_centerline": path_length,
        },
        "delta_length_um": path_length,
    }
    (Path(__file__).with_name("lengths.json")).write_text(json.dumps(lengths, indent=2))
    return c


if __name__ == "__main__":
    component = device()
    component.write_gds(Path(__file__).with_name("device.gds"), with_metadata=False)
