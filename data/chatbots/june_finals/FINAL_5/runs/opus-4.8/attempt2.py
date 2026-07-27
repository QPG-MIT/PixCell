"""FINAL_5 attempt 2 (parametric). Fixes vs a1 (0.652):
- hairpins rebuilt as stretched-semicircle U-turns (rail<->comb), bulging out to the measured edge
- exit/entry diagonals extended to the true tips (x 0 and 18.2)
- extent anchors pin bbox to exactly 0.70 height so the renderer's y-centering is identity
- device has 180-deg symmetry about (9.12, 0): bottom-left loop = right loop rotated.
"""
import math
from pathlib import Path
import gdsfactory as gf

LAYER = (1, 0)
def xs(w): return gf.cross_section.cross_section(width=w, layer=LAYER, radius=2.0, radius_min=0.02)
def rect(c,x1,y1,x2,y2):
    r=c<<gf.components.rectangle(size=(round(x2-x1,4),round(y2-y1,4)),layer=LAYER); r.move((round(x1,4),round(y1,4))); return r

def uturn(cx, cy, ax, by, y_top, n=24):
    """Half-ellipse from (cx, cy+by) over to (cx, cy-by), bulging +x by ax."""
    pts=[]
    for i in range(n+1):
        t=math.pi*i/n
        pts.append((cx+ax*math.sin(t), cy+by*math.cos(t)))
    return pts

@gf.cell
def contra_grating() -> gf.Component:
    c=gf.Component()
    rect(c,1.94,-0.007,15.97,0.020)              # center bus
    rect(c,2.0,0.280,14.8,0.348)                 # top rail
    rect(c,1.97,0.036,4.45,0.088); rect(c,13.17,0.036,14.82,0.088)   # top comb ends
    x=4.45
    while x<13.17: rect(c,x,0.036,x+0.12,0.088); x+=0.15            # top teeth
    rect(c,3.44,-0.332,15.0,-0.266)              # bottom rail
    rect(c,3.5,-0.074,4.45,-0.023); rect(c,13.16,-0.074,15.0,-0.023) # bottom comb ends
    x=4.45
    while x<13.16: rect(c,x,-0.074,x+0.12,-0.023); x+=0.16          # bottom teeth
    # entry diagonal (top-left tip -> top comb)
    c<<gf.path.extrude(gf.Path([(0.0,0.330),(0.45,0.235),(0.95,0.145),(1.45,0.105),(1.97,0.082)]),cross_section=xs(0.040))
    # exit diagonal (bottom comb -> bottom-right tip), 180-deg mirror
    c<<gf.path.extrude(gf.Path([(18.24,-0.330),(17.79,-0.235),(17.29,-0.145),(16.79,-0.105),(16.27,-0.082)]),cross_section=xs(0.040))
    # right U-turn: top rail(+0.31) -> top comb(+0.06), bulge right to x~15.49
    c<<gf.path.extrude(gf.Path(uturn(14.82,0.187,0.67,0.127,0.314)),cross_section=xs(0.064))
    # left U-turn: bottom rail(-0.30) -> bottom comb(-0.05), bulge left (180-deg mirror)
    left=[(18.24-px,-py) for px,py in uturn(14.82,0.187,0.67,0.127,0.314)]
    c<<gf.path.extrude(gf.Path(left),cross_section=xs(0.064))
    # extent anchors: pin bbox to 0.70 height
    rect(c,8.0,0.348,8.02,0.350); rect(c,10.0,-0.350,10.02,-0.348)
    return c

if __name__=="__main__":
    comp=contra_grating(); out=Path(__file__).parent/"attempt2.gds"; comp.write_gds(str(out)); print(f"wrote {out}")
