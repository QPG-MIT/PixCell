import numpy as np
from PIL import Image
from pathlib import Path
wd = Path(__file__).parent
arr = np.array(Image.open(wd / "component.png").convert("L"))
H, W = arr.shape
mask = arr < 245
X0, SX = 63, 200.05482456140354
def vx(px): return (px - X0) / SX
def vy(py): return (1152 - py) / SX   # visual y from bottom (isotropic)

def extent_in_yband(py0, py1, name):
    sub = mask[py0:py1]
    cols = np.where(sub.sum(axis=0) > 0)[0]
    if len(cols)==0:
        print(f"{name}: EMPTY"); return
    # require some density to avoid stray bend pixels: cols with >30% fill
    dens = sub.sum(axis=0)
    solid = np.where(dens > (py1-py0)*0.3)[0]
    print(f"{name}: any x px[{cols.min()},{cols.max()}] vx[{vx(cols.min()):.2f},{vx(cols.max()):.2f}] | dense(>30%) px[{solid.min() if len(solid) else -1},{solid.max() if len(solid) else -1}] vx[{vx(solid.min()) if len(solid) else 0:.2f},{vx(solid.max()) if len(solid) else 0:.2f}]")

print("=== BAND horizontal extents ===")
extent_in_yband(444,527,"TOP grating   (vy~3.33)")
extent_in_yband(551,598,"MIDDLE bus    (vy~2.89)")
extent_in_yband(623,706,"BOTTOM grating(vy~2.44)")
extent_in_yband(21,133, "TOP return wg (vy~5.37)")
extent_in_yband(1016,1124,"BOTTOM wg     (vy~0.41)")

# Bend bounding boxes: isolate regions by column, outside the central bands
print("\n=== corner/bend probing: y-segments at columns ===")
def segs(px):
    c = mask[:,px]; runs=[]; s=None
    for i in range(H):
        if c[i] and s is None: s=i
        elif not c[i] and s is not None: runs.append((s,i)); s=None
    if s is not None: runs.append((s,H))
    return [(a,b,round(vy(b),2),round(vy(a),2)) for a,b in runs]
# top-right hairpin rightmost, bottom-right taper, left hairpin
for px in [3060,3100,3140,3180,3220,3260,3300,3450,3550,3650,3690]:
    print(f" R px={px} vx={vx(px):.2f}: {segs(px)}")
print()
for px in [64,120,200,300,400,470,560,620,700,800]:
    print(f" L px={px} vx={vx(px):.2f}: {segs(px)}")

# middle bus exact right end
print("\n=== middle-bus right end scan (vy 2.89 band py551-598) ===")
for px in range(3150,3400,20):
    d = mask[551:598,px].sum()
    if d>0: print(f"  px={px} vx={vx(px):.2f} fill={d}/47")
