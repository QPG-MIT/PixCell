"""Parametric reconstruction of the `final1` target device from a B&W raster."""

from __future__ import annotations

import json
from pathlib import Path

import gdsfactory as gf

# Tunables (all top-level constants for optimizer mutability).
guide_width_stem_seg1 = 0.300
guide_width_stem_seg2 = 0.220
guide_width_stem_seg3 = 0.110
guide_width_top_1 = 0.100
guide_width_top_2 = 0.180
guide_width_top_3 = 0.300
guide_width_bottom_1 = 0.100
guide_width_bottom_2 = 0.180
guide_width_bottom_3 = 0.300
middle_y = 0.840
branch_start_x = 3.200
branch_mid_x = 24.800
right_end_x = 40.000
top_start_y = 0.570
top_mid_y = 0.570
top_end_y = 0.120
bottom_start_y = 1.110
bottom_mid_y = 1.220
bottom_end_y = 1.580
delta_length = 0.0

output_dir = Path(__file__).parent


@gf.cell
def device():
    """Create three disconnected tapered waveguide-like structures."""
    c = gf.Component()

    stem_path_1 = gf.Path([(0.0, middle_y), (8.0, middle_y)])
    stem_path_2 = gf.Path([(8.0, middle_y), (16.0, middle_y)])
    stem_path_3 = gf.Path([(16.0, middle_y), (branch_mid_x, middle_y)])
    top_path_1 = gf.Path([(branch_start_x, top_start_y), (20.0, top_mid_y)])
    top_path_2 = gf.Path([(20.0, top_mid_y), (30.5, 0.35)])
    top_path_3 = gf.Path([(30.5, 0.35), (right_end_x + delta_length, top_end_y)])
    bottom_path_1 = gf.Path([(branch_start_x, bottom_start_y), (20.0, bottom_mid_y)])
    bottom_path_2 = gf.Path([(20.0, bottom_mid_y), (30.5, 1.42)])
    bottom_path_3 = gf.Path([(30.5, 1.42), (right_end_x, bottom_end_y)])

    c << gf.path.extrude(stem_path_1, width=guide_width_stem_seg1, layer=(1, 0))
    c << gf.path.extrude(stem_path_2, width=guide_width_stem_seg2, layer=(1, 0))
    c << gf.path.extrude(stem_path_3, width=guide_width_stem_seg3, layer=(1, 0))
    c << gf.path.extrude(top_path_1, width=guide_width_top_1, layer=(1, 0))
    c << gf.path.extrude(top_path_2, width=guide_width_top_2, layer=(1, 0))
    c << gf.path.extrude(top_path_3, width=guide_width_top_3, layer=(1, 0))
    c << gf.path.extrude(bottom_path_1, width=guide_width_bottom_1, layer=(1, 0))
    c << gf.path.extrude(bottom_path_2, width=guide_width_bottom_2, layer=(1, 0))
    c << gf.path.extrude(bottom_path_3, width=guide_width_bottom_3, layer=(1, 0))

    arms = {
        "top": top_path_1.length() + top_path_2.length() + top_path_3.length(),
        "bottom": bottom_path_1.length() + bottom_path_2.length() + bottom_path_3.length(),
    }
    lengths = {
        "arms": arms,
        "delta_length_um": arms["top"] - arms["bottom"],
    }

    c.write_gds(output_dir / "device.gds", with_metadata=False)
    (output_dir / "lengths.json").write_text(json.dumps(lengths, indent=2))
    return c


def _write_device_gds() -> Path:
    c = device()
    gds_path = output_dir / "device.gds"
    c.write_gds(gds_path, with_metadata=False)
    return gds_path


if __name__ == "__main__":
    _write_device_gds()
