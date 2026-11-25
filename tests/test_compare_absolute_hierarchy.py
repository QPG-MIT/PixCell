"""The canonical metric must retain transforms on the actual device root."""

import math

import gdstk
import numpy as np
import pytest

from michaelangelo.core.compare_absolute import extract_polygons, gds_bbox


@pytest.mark.parametrize("with_metadata", [False, True])
def test_nested_rotated_reflected_device_retains_root_pose(tmp_path, with_metadata):
    child = gdstk.Cell("child")
    child.add(gdstk.rectangle((0, 0), (4, 1), layer=1))
    middle = gdstk.Cell("middle")
    middle.add(gdstk.Reference(child, origin=(10, 20), rotation=math.pi / 2, x_reflection=True))
    device = gdstk.Cell("device")
    device.add(gdstk.Reference(middle, origin=(30, 50), rotation=math.pi))
    # Child-first ordering reproduces the historical count-tie failure.
    library = gdstk.Library()
    library.add(child, middle, device)
    if with_metadata:
        metadata = gdstk.Cell("$$$CONTEXT_INFO$$$")
        metadata.add(*(gdstk.Reference(cell) for cell in (child, middle, device)))
        library.add(metadata)
    path = tmp_path / "device.gds"
    library.write_gds(path)

    polygons = extract_polygons(path)
    assert len(polygons) == 1
    assert gds_bbox(polygons) == pytest.approx((19, 26, 20, 30))
    assert sorted(map(tuple, np.round(polygons[0], 8))) == [(19, 26), (19, 30), (20, 26), (20, 30)]


def test_multiple_device_roots_preserve_largest_polygon_count_choice(tmp_path):
    small = gdstk.Cell("small")
    small.add(gdstk.rectangle((0, 0), (1, 1), layer=1))
    large = gdstk.Cell("large")
    large.add(gdstk.rectangle((10, 10), (11, 11), layer=1))
    large.add(gdstk.rectangle((12, 10), (13, 11), layer=1))
    library = gdstk.Library()
    library.add(small, large)
    path = tmp_path / "roots.gds"
    library.write_gds(path)

    polygons = extract_polygons(path)
    assert len(polygons) == 2
    assert gds_bbox(polygons) == pytest.approx((10, 10, 13, 11))
