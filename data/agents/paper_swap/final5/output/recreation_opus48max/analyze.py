"""Measure the target silhouette. Image is the ONLY ground truth."""
import numpy as np
from PIL import Image
from pathlib import Path

wd = Path(__file__).parent
img = Image.open(wd / "component.png").convert("L")
arr = np.array(img)
H, W = arr.shape
mask = arr < 245  # black = material
print(f"image {W}x{H}, black px {mask.sum()}")

ys, xs = np.where(mask)
x0, y0, x1, y1 = xs.min(), ys.min(), xs.max() + 1, ys.max() + 1
print(f"black bbox px: x[{x0},{x1}] y[{y0},{y1}]  size {x1-x0}x{y1-y0}")

# calibration mapping helpers
X0, Y0 = 63, 18
SX, SY = 200.05482456140354, 1620.0
BBOX_H = 1134
def x_um(px): return (px - X0) / SX
def y_um(py): return 0.7 * (1152 - py) / BBOX_H

# ---- ROW PROFILE (black count per row, full width) ----
row = mask.sum(axis=1)
print("\n=== ROW PROFILE (every 20th row with black) ===")
# find bands: rows where black count > small threshold
active = row > 5
# segment into contiguous bands
bands = []
start = None
for i in range(H):
    if active[i] and start is None:
        start = i
    elif not active[i] and start is not None:
        bands.append((start, i)); start = None
if start is not None: bands.append((start, H))
print(f"{len(bands)} horizontal bands (row segments):")
for (a, b) in bands:
    seg = row[a:b]
    print(f"  py[{a},{b}] h={b-a}px  y_um[{y_um(b):.3f},{y_um(a):.3f}]  maxblack={seg.max()} meanblack={seg.mean():.0f}")

# ---- COLUMN PROFILE (black count per col, full height) ----
col = mask.sum(axis=0)
print("\n=== COLUMN PROFILE landmarks ===")
active_c = col > 5
segs = []
start = None
for i in range(W):
    if active_c[i] and start is None:
        start = i
    elif not active_c[i] and start is not None:
        segs.append((start, i)); start = None
if start is not None: segs.append((start, W))
print(f"{len(segs)} column segments (x-extent of content): {segs[:3]}...{segs[-2:]}")
print(f"content x range px [{segs[0][0]},{segs[-1][1]}]  x_um[{x_um(segs[0][0]):.2f},{x_um(segs[-1][1]):.2f}]")

# ---- Identify the central grating region: look at mid-height horizontal slices ----
print("\n=== HORIZONTAL SLICES (row profile at chosen py to find bands) ===")
for py in [140, 340, 480, 560, 640, 720, 900, 1050]:
    r = mask[py]
    runs = []
    s = None
    for i in range(W):
        if r[i] and s is None: s = i
        elif not r[i] and s is not None: runs.append((s, i)); s = None
    if s is not None: runs.append((s, W))
    nblack = r.sum()
    print(f" py={py} (y_um={y_um(py):.3f}): {len(runs)} black runs, total black={nblack}")
