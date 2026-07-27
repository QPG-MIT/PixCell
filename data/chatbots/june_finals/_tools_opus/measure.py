"""Independent image-measurement helper (Opus 4.8 runs).

Usage: measure.py <device_dir> ... prints calibrated cross-section scans.
Reads device_bw.png (or component.png) + the opus calibration.json.
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image


def load(device_dir: Path):
    calib = json.loads((device_dir / "runs/opus-4.8/component/calibration.json").read_text())
    img_path = device_dir / "device_bw.png"
    if not img_path.exists():
        img_path = device_dir / "component.png"
    img = np.array(Image.open(img_path).convert("L"))
    black = img < calib["white_threshold"]
    sx, sy = calib["scale_px_per_um"]
    x0 = calib["bbox"][0]
    yc = (calib["bbox"][1] + calib["bbox"][3]) / 2
    return black, sx, sy, x0, yc


def runs(arr, minlen=2):
    out, start = [], None
    for i in range(len(arr)):
        if arr[i] and start is None:
            start = i
        elif not arr[i] and start is not None:
            if i - start >= minlen:
                out.append((start, i - 1))
            start = None
    if start is not None:
        out.append((start, len(arr) - 1))
    return out


if __name__ == "__main__":
    device_dir = Path(sys.argv[1])
    black, sx, sy, x0, yc = load(device_dir)
    H, W = black.shape
    xu = lambda p: (p - x0) / sx
    yu = lambda p: (yc - p) / sy
    xp = lambda u: int(round(u * sx + x0))
    ypx = lambda u: int(round(yc - u * sy))
    print(f"image {W}x{H}  sx={sx:.3f} sy={sy:.3f} x0={x0} yc={yc}")
    ink_rows = np.where(black.any(axis=1))[0]
    ink_cols = np.where(black.any(axis=0))[0]
    print(f"ink x_um [{xu(ink_cols[0]):.3f},{xu(ink_cols[-1]):.3f}] "
          f"y_um [{yu(ink_rows[-1]):.3f},{yu(ink_rows[0]):.3f}]")
    # column scans across the width
    print("=== COLUMN SCANS (x_um -> y-bands [lo,hi] w) ===")
    for frac in [0.005, 0.02, 0.05, 0.1, 0.2, 0.35, 0.5, 0.65, 0.8, 0.9, 0.95, 0.98, 0.995]:
        x = xu(ink_cols[0]) + frac * (xu(ink_cols[-1]) - xu(ink_cols[0]))
        rs = runs(black[:, xp(x)])
        bands = " ; ".join(f"[{yu(b):+.3f},{yu(a):+.3f}]w{(b-a+1)/sy:.3f}" for a, b in rs[:12])
        print(f"x={x:7.3f}: n={len(rs)} {bands}")
