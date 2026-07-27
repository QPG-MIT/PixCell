"""Independent reconstruction-tier tracer (Opus 4.8).

Samples the calibrated target in horizontal strips, emits one rectangle per
black run, expressed via gf.components.rectangle. Writes the GDS directly.

Usage: recon.py <device_dir> <step_um> <out.gds> [edge_inset_frac]
edge_inset_frac (default 0.5) trims each run by a fraction of a strip edge
to counter the half-pixel overfill of axis-aligned fills.
"""
import json
import sys
from pathlib import Path

import gdsfactory as gf
import numpy as np
from PIL import Image

LAYER = (1, 0)


def main(device_dir: Path, step: float, out: Path, inset: float):
    calib = json.loads((device_dir / "runs/opus-4.8/component/calibration.json").read_text())
    img_path = device_dir / "device_bw.png"
    if not img_path.exists():
        img_path = device_dir / "component.png"
    black = np.array(Image.open(img_path).convert("L")) < calib["white_threshold"]
    sx, sy = calib["scale_px_per_um"]
    x0 = calib["bbox"][0]
    by1, by2 = calib["bbox"][1], calib["bbox"][3]
    yc = (by1 + by2) / 2
    xu = lambda p: (p - x0) / sx
    y_top = (yc - by1) / sy
    px_in = inset / sx

    c = gf.Component()
    y = y_top
    H = black.shape[0]
    while y > -y_top - 1e-9:
        row = int(round(yc - (y - step / 2) * sy))
        if 0 <= row < H:
            r = black[row, :]
            runs, s = [], None
            for i, v in enumerate(r):
                if v and s is None:
                    s = i
                elif not v and s is not None:
                    if i - s >= 2:
                        runs.append((s, i - 1))
                    s = None
            if s is not None:
                runs.append((s, len(r) - 1))
            for a, b in runs:
                xa, xb = xu(a) + px_in, xu(b + 1) - px_in
                w, h = round(xb - xa, 4), round(step, 4)
                if w > 0 and h > 0:
                    rr = c << gf.components.rectangle(size=(w, h), layer=LAYER)
                    rr.move((round(xa, 4), round(y - step, 4)))
        y -= step
    c.write_gds(str(out))
    print(f"wrote {out}")


if __name__ == "__main__":
    device_dir, step, out = Path(sys.argv[1]), float(sys.argv[2]), Path(sys.argv[3])
    inset = float(sys.argv[4]) if len(sys.argv) > 4 else 0.5
    main(device_dir, step, out, inset)
