#!/usr/bin/env python3
"""
Compute SSE (Sum of Squared Errors) for GDS vs target comparison
"""

import argparse
import json
from pathlib import Path
import numpy as np
from PIL import Image


def compute_sse_metrics(target_path: Path, raster_path: Path, white_threshold: int = 245) -> dict:
    """Compute SSE and related metrics between target and raster images"""

    # Load images
    target_img = np.array(Image.open(target_path).convert("L"))
    raster_img = np.array(Image.open(raster_path).convert("L"))

    # Binarize (0 = white, 1 = black)
    target_binary = (target_img < white_threshold).astype(np.float32)
    raster_binary = (raster_img < white_threshold).astype(np.float32)

    # Compute pixel-wise differences
    diff = target_binary - raster_binary

    # Sum of Squared Errors
    sse = float(np.sum(diff ** 2))

    # Mean Squared Error
    total_pixels = target_binary.size
    mse = sse / total_pixels

    # Root Mean Squared Error
    rmse = np.sqrt(mse)

    # Additional breakdown
    both_black = np.logical_and(target_binary == 1, raster_binary == 1).sum()
    both_white = np.logical_and(target_binary == 0, raster_binary == 0).sum()
    target_only = np.logical_and(target_binary == 1, raster_binary == 0).sum()  # False negatives
    raster_only = np.logical_and(target_binary == 0, raster_binary == 1).sum()  # False positives

    # Pixel counts
    target_black_total = target_binary.sum()
    raster_black_total = raster_binary.sum()

    # Normalized SSE: fraction of pixels wrong (0-1 range, comparable across images)
    normalized_sse = sse / total_pixels if total_pixels > 0 else 0.0

    # IoU from binary masks (for cross-component comparison)
    intersection = float(both_black)
    union = float(both_black + target_only + raster_only)
    iou = intersection / union if union > 0 else 0.0

    return {
        "SSE": sse,
        "normalized_SSE": normalized_sse,
        "IoU": iou,
        "MSE": mse,
        "RMSE": rmse,
        "total_pixels": int(total_pixels),
        "error_pixels": int(sse),  # Since binary, squared errors = count of errors
        "breakdown": {
            "both_black": int(both_black),
            "both_white": int(both_white),
            "missing_black": int(target_only),  # False negatives
            "extra_black": int(raster_only),    # False positives
        },
        "target_black_pixels": int(target_black_total),
        "raster_black_pixels": int(raster_black_total),
        "accuracy": float((both_black + both_white) / total_pixels),
    }


def main():
    parser = argparse.ArgumentParser(description="Compute SSE between target and raster")
    parser.add_argument("--target", type=Path, required=True, help="Target image (e.g., 1.png)")
    parser.add_argument("--raster", type=Path, required=True, help="Rasterized GDS image")
    parser.add_argument("--white-threshold", type=int, default=245, help="White threshold (default: 245)")
    parser.add_argument("--out", type=Path, help="Output JSON file (optional)")

    args = parser.parse_args()

    # Compute metrics
    metrics = compute_sse_metrics(args.target, args.raster, args.white_threshold)

    # Print results
    print(json.dumps(metrics, indent=2))

    # Save to file if requested
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with open(args.out, "w") as f:
            json.dump(metrics, f, indent=2)
        print(f"\n✓ Saved to {args.out}")


if __name__ == "__main__":
    main()
