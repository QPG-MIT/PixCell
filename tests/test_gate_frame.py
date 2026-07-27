"""The gate-frame convention: every surface that draws or scores polygons
against the calibrated target must use render_gds_absolute's anchoring
(left edge to target bbox, vertically centered on the footprint).

Regression for the studio light-table misalignment: a program whose bbox is
centered on the origin (e.g. the 1x4 splitter, x in [-2.5, 2.5]) drew beside
its target ghost instead of on it, while the gate scored it correctly.
"""

import numpy as np
import pytest

from michaelangelo.core.compare_absolute import (
    gate_frame_offset,
    gds_bbox,
    render_gds_absolute,
)


def test_offset_for_origin_centered_bbox():
    # x in [-2.5, 2.5], y in [0, 24.3] on a 24.3 um-tall footprint —
    # the 1x4 splitter's exact shape of failure
    polys = [[(-2.5, 0.0), (2.5, 0.0), (2.5, 24.3), (-2.5, 24.3)]]
    dx, dy = gate_frame_offset(polys, (5.0, 24.3))
    assert dx == pytest.approx(2.5)
    assert dy == pytest.approx(0.0)
    assert isinstance(dx, float) and not isinstance(dx, np.floating)


def test_offset_identity_for_origin_anchored_full_height():
    polys = [[(0.0, 0.0), (5.0, 0.0), (5.0, 24.3), (0.0, 24.3)]]
    dx, dy = gate_frame_offset(polys, (5.0, 24.3))
    assert dx == pytest.approx(0.0)
    assert dy == pytest.approx(0.0)


def test_offset_centers_short_device_vertically():
    # a 10 um-tall device on a 24 um footprint centers at 12: dy = 12 - 5 = 7
    polys = [[(1.0, 0.0), (3.0, 0.0), (3.0, 10.0), (1.0, 10.0)]]
    dx, dy = gate_frame_offset(polys, (5.0, 24.0))
    assert dx == pytest.approx(-1.0)
    assert dy == pytest.approx(7.0)


def test_translated_polygons_render_identically():
    """The gate is translation-invariant by construction; the normalized
    polygons must rasterize to the exact same mask as the originals."""
    calib = {
        "image_size_px": (200, 300),
        "scale_px_per_um": (10.0, 10.0),
        "bbox": (20, 30, 120, 280),
        "footprint_um": (10.0, 25.0),
    }
    polys = [[(-4.0, 2.0), (4.0, 2.0), (4.0, 20.0), (-4.0, 20.0)]]
    dx, dy = gate_frame_offset(polys, calib["footprint_um"])
    moved = [[(x + dx, y + dy) for x, y in poly] for poly in polys]
    r1, _ = render_gds_absolute(polys, calib)
    r2, _ = render_gds_absolute(moved, calib)
    assert np.array_equal(np.array(r1), np.array(r2))
    # and the normalized set really is in the gate frame
    gx0, gy0, gx1, gy1 = gds_bbox(moved)
    assert gx0 == pytest.approx(0.0)
    assert (gy0 + gy1) / 2 == pytest.approx(calib["footprint_um"][1] / 2)
