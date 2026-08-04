#!/usr/bin/env python3
"""Compare GDS to image using FIXED calibration parameters"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List, Sequence, Tuple

import numpy as np
from PIL import Image

try:
    pass  # type: ignore
except Exception as e:
    raise SystemExit("gdstk is required. Install with: pip install gdstk") from e

# Import from gds_raster_compare.py
# Handle both script and module import contexts
try:
    from . import gds_raster_compare as cmp
except ImportError:
    import gds_raster_compare as cmp


def load_calibration(cal_path: Path) -> dict:
    """Load calibration parameters"""
    with cal_path.open() as f:
        return json.load(f)


def map_polygons_with_fixed_calibration(
    polygons: Sequence[np.ndarray],
    layout_bbox: Tuple[float, float, float, float],
    calibration: dict,
    out_size: Tuple[int, int],
    flip_y: bool,
    supersample: int,
) -> List[List[Tuple[int, int]]]:
    """Map polygons using FIXED calibration parameters.

    X-AXIS: LEFT-ALIGNED - GDS left edge aligns with target bbox left edge.
    Y-AXIS: CENTERED - GDS is vertically centered in the target bbox.

    Uses fixed offset and scaling from calibration instead of recalculating bbox.
    """
    lx0, ly0, lx1, ly1 = layout_bbox

    # Use calibration parameters
    dx, dy = calibration["offset"]
    sx, sy = calibration["scale_px_per_um"]
    footprint_length, footprint_width = calibration["footprint_um"]

    # Calculate scaling based on footprint, not actual GDS bbox
    # This ensures consistent scaling for all devices
    scale_x = sx  # Already: bbox_width / footprint_length
    scale_y = sy  # Already: bbox_height / footprint_width

    # GDS center Y for vertical centering
    gds_cy = 0.5 * (ly0 + ly1)
    # Footprint center Y
    target_cy = 0.5 * footprint_width

    mapped: List[List[Tuple[int, int]]] = []
    for poly in polygons:
        if poly.size == 0:
            continue
        pts = []
        for x, y in poly:
            # X-AXIS: LEFT-ALIGNED - relative to GDS left edge
            x_rel = x - lx0

            # Y-AXIS: CENTERED - relative to GDS center, then shift to footprint center
            y_centered = y - gds_cy + target_cy

            # Apply fixed scaling and offset
            # GDS left edge (x_rel=0) → target bbox left edge (dx)
            x_pixel = x_rel * scale_x + dx

            if flip_y:
                # Y-flip with centering
                y_pixel = dy + (footprint_width - y_centered) * scale_y
            else:
                y_pixel = dy + y_centered * scale_y

            pts.append((int(round(x_pixel * supersample)), int(round(y_pixel * supersample))))
        mapped.append(pts)
    return mapped


def main() -> None:
    p = argparse.ArgumentParser(
        description="Compare GDS to image using FIXED calibration parameters"
    )
    p.add_argument("--gds", required=True, type=Path)
    p.add_argument("--layer", required=True, type=int)
    p.add_argument("--datatype", required=True, type=int)
    p.add_argument("--calibration", required=True, type=Path,
                   help="Calibration JSON file (from calibrate_boundary.py)")
    p.add_argument("--like", required=True, type=Path,
                   help="Reference image (for size only)")
    p.add_argument("--flip-y", action="store_true")
    p.add_argument("--supersample", type=int, default=4)
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--compare-to", required=True, type=Path)
    p.add_argument("--diff", required=True, type=Path)
    p.add_argument("--overlay", required=True, type=Path)
    p.add_argument("--report", required=True, type=Path)
    args = p.parse_args()
    
    # Load calibration
    cal = load_calibration(args.calibration)
    
    # Load GDS
    top = cmp.load_top_cell(args.gds)
    polys = cmp.extract_polygons(top, args.layer, args.datatype)
    if not polys:
        raise SystemExit("No polygons found for specified (layer, datatype)")
    lx0, ly0, lx1, ly1 = cmp.polygons_bbox(polys)
    
    # Get image size
    like_img = Image.open(args.like)
    W, H = like_img.size
    
    # Map using fixed calibration
    mapped = map_polygons_with_fixed_calibration(
        polygons=polys,
        layout_bbox=(lx0, ly0, lx1, ly1),
        calibration=cal,
        out_size=(W, H),
        flip_y=args.flip_y,
        supersample=args.supersample,
    )
    
    # Rasterize
    Wss, Hss = W * args.supersample, H * args.supersample
    raster_ss = cmp.rasterize(mapped, (Wss, Hss))
    raster = raster_ss.resize((W, H), resample=Image.BOX)
    raster.save(args.out)
    
    # Compare
    target = Image.open(args.compare_to)
    mask_g = cmp.binarize(raster, white_threshold=cal["white_threshold"])
    mask_t = cmp.binarize(target, white_threshold=cal["white_threshold"])
    
    metrics = cmp.compute_metrics(mask_g, mask_t)
    args.report.write_text(json.dumps(metrics, indent=2))
    
    diff_img = cmp.make_diff(mask_g, mask_t)
    diff_img.save(args.diff)
    overlay_img = cmp.make_overlay(target, mask_g)
    overlay_img.save(args.overlay)
    
    print(json.dumps(metrics, indent=2))
    print("\n✓ Used fixed calibration:")
    print(f"  Offset: {cal['offset']}")
    print(f"  Scale: {cal['scale_px_per_um'][0]:.3f} px/μm (x), {cal['scale_px_per_um'][1]:.3f} px/μm (y)")


if __name__ == "__main__":
    main()

