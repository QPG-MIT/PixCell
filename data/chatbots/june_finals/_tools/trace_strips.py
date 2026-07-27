"""Generic bitmap-to-strips tracer for the reconstruction tier.

Samples the calibrated target image in horizontal strips and emits, for each
strip, every black run as (y_top, y_bot, x_left, x_right) in um. The output
data file is consumed by a GDSFactory script that places one rectangle per run.

Usage: python trace_strips.py <device_dir> <step_um> <out_py>
where <device_dir> contains device_bw.png and runs/claude-fable-5/component/calibration.json
"""

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image


def trace(device_dir: Path, step: float):
    calib = json.loads((device_dir / "runs/claude-fable-5/component/calibration.json").read_text())
    img = np.array(Image.open(device_dir / "device_bw.png").convert("L"))
    black = img < calib["white_threshold"]
    sx, sy = calib["scale_px_per_um"]
    x0, (by1, by2) = calib["bbox"][0], (calib["bbox"][1], calib["bbox"][3])
    yc = (by1 + by2) / 2
    xu = lambda p: (p - x0) / sx
    yu_top = (yc - by1) / sy

    strips = []
    y = yu_top
    while y > -yu_top - 1e-9:
        row = int(round(yc - (y - step / 2) * sy))
        if 0 <= row < black.shape[0]:
            r = black[row, :]
            edges = np.flatnonzero(np.diff(r.astype(np.int8)))
            starts = list(edges[::2] + 1) if r[0] == 0 else [0] + list(edges[1::2] + 1)
            # simpler robust run finder
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
                strips.append((round(y, 4), round(y - step, 4), round(xu(a), 4), round(xu(b + 1), 4)))
        y -= step
    return strips


if __name__ == "__main__":
    device_dir, step, out = Path(sys.argv[1]), float(sys.argv[2]), Path(sys.argv[3])
    strips = trace(device_dir, step)
    out.write_text("STRIPS = " + repr(strips) + "\n")
    print(f"{len(strips)} strips -> {out}")
