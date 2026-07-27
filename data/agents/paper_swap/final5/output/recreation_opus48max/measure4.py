import numpy as np
from PIL import Image
from pathlib import Path
wd = Path(__file__).parent
arr = np.array(Image.open(wd / "component.png").convert("L"))
H, W = arr.shape
mask = arr < 245
X0, SX = 63, 200.05482456140354
def vx(px): return (px - X0) / SX
def vy(py): return (1152 - py) / SX

print("=== TOP extreme rows (find topmost content x-range) ===")
for py in range(16, 40, 3):
    xs = np.where(mask[py])[0]
    if len(xs): print(f"  py={py} vy={vy(py):.3f}: x px[{xs.min()},{xs.max()}] vx[{vx(xs.min()):.2f},{vx(xs.max()):.2f}] n={len(xs)}")
print("=== BOTTOM extreme rows ===")
for py in range(1120, 1152, 4):
    xs = np.where(mask[py])[0]
    if len(xs): print(f"  py={py} vy={vy(py):.3f}: x px[{xs.min()},{xs.max()}] vx[{vx(xs.min()):.2f},{vx(xs.max()):.2f}] n={len(xs)}")

# TOP-RIGHT hairpin outer/inner: for each py in the hairpin, rightmost x
print("\n=== TOP-RIGHT hairpin: rightmost x per row (py 60..540) ===")
for py in range(70, 540, 30):
    row = mask[py, 2900:]
    xs = np.where(row)[0]
    if len(xs): print(f"  py={py} vy={vy(py):.3f}: right x px={2900+xs.max()} vx={vx(2900+xs.max()):.2f}  (seg count {len(np.where(np.diff(xs)>3)[0])+1})")

# BOTTOM-LEFT hairpin: leftmost x per row (py 620..1130)
print("\n=== BOTTOM-LEFT hairpin: leftmost x per row (py 620..1120) ===")
for py in range(640, 1120, 30):
    row = mask[py, :1000]
    xs = np.where(row)[0]
    if len(xs): print(f"  py={py} vy={vy(py):.3f}: left x px={xs.min()} vx={vx(xs.min()):.2f}")

# INPUT curve centerline (top-left, x 64..430), and needle taper (top return) center
print("\n=== INPUT curve centerline (top strand descending) & needle taper ===")
for px in range(70, 440, 40):
    col = mask[:600, px]  # upper half only
    ys = np.where(col)[0]
    if len(ys):
        # split into runs
        runs=[]; s=ys[0]; p=ys[0]
        for y in ys[1:]:
            if y-p>3: runs.append((s,p)); s=y
            p=y
        runs.append((s,p))
        print(f"  px={px} vx={vx(px):.2f}: runs vy=" + " ".join(f"[{vy(b):.2f},{vy(a):.2f}]" for a,b in runs))
