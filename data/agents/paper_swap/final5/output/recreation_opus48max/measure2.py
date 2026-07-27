import numpy as np
from PIL import Image
from pathlib import Path

wd = Path(__file__).parent
arr = np.array(Image.open(wd / "component.png").convert("L"))
H, W = arr.shape
mask = arr < 245
X0, SX, SY, BBOX_H = 63, 200.05482456140354, 1620.0, 1134
def x_um(px): return (px - X0) / SX
def y_um(py): return 0.7 * (1152 - py) / BBOX_H

def band_geom(py_lo, py_hi, label):
    """Within a py window, find the solid horizontal element's exact y-center/thickness
    (using columns where it's densest) and x-extent."""
    sub = mask[py_lo:py_hi]
    colcount = sub.sum(axis=0)
    xs = np.where(colcount > 0)[0]
    print(f"\n[{label}] window py[{py_lo},{py_hi}] x px[{xs.min()},{xs.max()}] x_um[{x_um(xs.min()):.2f},{x_um(xs.max()):.2f}]")
    return xs.min(), xs.max()

# The three central elements from earlier: top grating ~py444-527, middle bus ~py551-597, bottom ~py623-706
# Refine y-bands by scanning row density over a solid column region (middle, e.g. px 1500-2500)
region = mask[:, 1500:2500]
rowden = region.mean(axis=1)  # fraction black per row in mid region
print("=== row density (mid x 1500-2500), rows with >0.1 ===")
prev = False
for py in range(H):
    on = rowden[py] > 0.1
    if on and not prev: start = py
    if (not on) and prev:
        seg = rowden[start:py]
        print(f"  py[{start},{py}] h={py-start} yum[{y_um(py):.3f},{y_um(start):.3f}] center_yum={y_um((start+py)/2):.3f} maxden={seg.max():.2f}")
    prev = on

# ---- Grating period/count via column profile in a clean grating band ----
def grating_stats(py_c, half, label, xa, xb):
    band = mask[py_c-half:py_c+half, xa:xb]
    prof = band.sum(axis=0).astype(float)  # per-column black count
    b = (prof > half*0.5).astype(int)  # column is "tooth" if >half-height covered
    # count rising edges = teeth
    edges = np.where(np.diff(b) == 1)[0]
    teeth = len(edges) + (1 if b[0] == 1 else 0)
    # period via mean spacing of rising edges
    if len(edges) > 2:
        per = np.median(np.diff(edges))
    else:
        per = float('nan')
    duty = b.mean()
    print(f"\n[{label}] band py_c={py_c} x px[{xa},{xb}] len_um={x_um(xb)-x_um(xa):.3f}")
    print(f"   teeth={teeth} period_px={per:.2f} period_um={per/SX:.4f} duty={duty:.2f}")
    return teeth, per, edges, xa

# top grating spans x_um[1.83,14.89] -> px[429,3041]; bottom x_um[4.43,15.33]->px[949,3129]
tt = grating_stats(485, 40, "TOP grating", 429, 3041)
bt = grating_stats(664, 40, "BOT grating", 949, 3129)

# ---- Spine check: in a gap column, is there any black in the band? ----
print("\n=== SPINE CHECK top grating: min gray in gap columns within band py[450,520] ===")
# find gap columns (low coverage)
band = mask[450:520, 429:3041]
prof = band.sum(axis=0)
gapcols = np.where(prof < 5)[0][:5] + 429
print("sample gap columns:", gapcols.tolist())
for gc in gapcols:
    strip = arr[450:520, gc]
    print(f"  gap px x={gc}: min_gray={strip.min()} (black<245 -> {'HAS material' if strip.min()<245 else 'fully white=no spine'})")

# ---- Phase alignment top vs bottom teeth ----
if len(tt[2]) > 3 and len(bt[2]) > 3:
    top_edges = tt[2] + tt[3]
    bot_edges = bt[2] + bt[3]
    # compare positions in overlap region
    print("\n=== PHASE: first 6 top tooth edges px:", top_edges[:6].tolist())
    print("=== PHASE: first 6 bot tooth edges px:", bot_edges[:6].tolist())

# ---- Taper tips & waveguide widths at key columns ----
print("\n=== TAPER / routing sample columns (y-segments) ===")
def segs_at(px):
    c = mask[:, px]
    runs=[]; s=None
    for i in range(H):
        if c[i] and s is None: s=i
        elif not c[i] and s is not None: runs.append((s,i)); s=None
    if s is not None: runs.append((s,H))
    return [(a,b,b-a,round(y_um(b),3),round(y_um(a),3)) for a,b in runs]
for px in [64, 100, 200, 430, 520, 900, 3040, 3200, 3400, 3600, 3700]:
    print(f" px={px} x_um={x_um(px):.2f}: {segs_at(px)}")
