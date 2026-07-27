#!/usr/bin/env python3
"""Calculate and store calibration parameters for fixed boundary mapping"""

import json
from pathlib import Path
from PIL import Image
import numpy as np


def calculate_calibration(
    reference_image: Path,
    footprint_length_um: float,
    footprint_width_um: float,
    white_threshold: int = 245,
) -> dict:
    """Calculate calibration parameters from a reference image and footprint size.
    
    Returns:
        dict with:
        - bbox: [x0, y0, x1, y1] pixel coordinates
        - offset: [dx, dy] where to start positioning
        - scale: [sx, sy] scaling factors px/μm
        - footprint_um: [length, width] in microns
    """
    img = Image.open(reference_image)
    W, H = img.size
    
    # Find non-white bbox
    arr = np.array(img.convert("L"))
    mask = arr < white_threshold
    if not mask.any():
        bbox = [0, 0, W, H]
    else:
        ys, xs = np.where(mask)
        bbox = [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]
    
    x0, y0, x1, y1 = bbox
    bbox_width = x1 - x0
    bbox_height = y1 - y0
    
    # Calculate scaling factors
    sx = bbox_width / footprint_length_um
    sy = bbox_height / footprint_width_um
    
    return {
        "bbox": bbox,
        "bbox_size_px": [bbox_width, bbox_height],
        "offset": [x0, y0],
        "scale_px_per_um": [sx, sy],
        "footprint_um": [footprint_length_um, footprint_width_um],
        "image_size_px": [W, H],
        "white_threshold": white_threshold,
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Calculate calibration parameters for fixed boundary mapping"
    )
    parser.add_argument("--reference-image", type=Path, required=True,
                       help="Reference image (e.g., flow_step_04.png)")
    parser.add_argument("--footprint-length-um", type=float, required=True,
                       help="Footprint length in microns")
    parser.add_argument("--footprint-width-um", type=float, required=True,
                       help="Footprint width in microns")
    parser.add_argument("--white-threshold", type=int, default=245,
                       help="White threshold for bbox detection")
    parser.add_argument("--out", type=Path, default=Path("calibration.json"),
                       help="Output calibration JSON file")
    args = parser.parse_args()
    
    cal = calculate_calibration(
        args.reference_image,
        args.footprint_length_um,
        args.footprint_width_um,
        args.white_threshold,
    )
    
    args.out.write_text(json.dumps(cal, indent=2))
    print(f"Calibration saved to {args.out}")
    print("\nCalibration parameters:")
    print(f"  Bbox: {cal['bbox']}")
    print(f"  Offset: {cal['offset']}")
    print(f"  Scale: {cal['scale_px_per_um'][0]:.6f} px/μm (x), {cal['scale_px_per_um'][1]:.6f} px/μm (y)")
    print(f"  Footprint: {cal['footprint_um'][0]} × {cal['footprint_um'][1]} μm")


if __name__ == "__main__":
    main()

