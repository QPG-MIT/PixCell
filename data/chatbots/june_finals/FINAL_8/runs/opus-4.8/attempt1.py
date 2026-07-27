"""FINAL_8: multi-stripe coupler (120 x 4 um). Attempt 1 (parametric).

Independent measurement (Opus 4.8). Top/bottom mirror symmetric.
- 5 center stripes spanning the full width (x[0,120])
- top slab y[0.267,0.738] + 5-stripe grating above, flat over x[11,109]
- bundles sweep up/out at both top corners (and down at bottom corners)
"""
from pathlib import Path
import gdsfactory as gf

LAYER=(1,0)
def xs(w): return gf.cross_section.cross_section(width=w, layer=LAYER, radius=3.0, radius_min=0.05)
def rect(c,x1,y1,x2,y2):
    r=c<<gf.components.rectangle(size=(round(x2-x1,4),round(y2-y1,4)),layer=LAYER); r.move((round(x1,4),round(y1,4))); return r

CENTER=[(0.160,0.230),(0.060,0.130),(-0.037,0.024),(-0.138,-0.074),(-0.243,-0.173)]
TOPSTRIPES=[(0.768,0.836),(0.868,0.936),(0.969,1.036),(1.068,1.136),(1.168,1.236)]

@gf.cell
def stripe_coupler() -> gf.Component:
    c=gf.Component()
    # full-width center stripes
    for y1,y2 in CENTER: rect(c,0.0,y1,120.0,y2)
    for s in (1,-1):
        # slab
        rect(c,11.0, s*0.267 if s>0 else -0.738, 109.0, s*0.738 if s>0 else -0.267)
        # grating stripes
        for y1,y2 in TOPSTRIPES:
            rect(c,11.0, s*y1 if s>0 else -y2, 109.0, s*y2 if s>0 else -y1)
        # corner sweeps: slab + bundle curve out to the top/bottom edge
        for xc, xtip in [(11.0, 5.0),(109.0,115.0)]:
            sgn = 1 if xc<60 else -1   # sweep direction
            # slab sweep
            c<<gf.path.extrude(gf.Path([(xc, s*0.5),(xc-sgn*3, s*1.0),(xc-sgn*5.5, s*1.6),(xtip, s*1.95)]),cross_section=xs(0.47))
            # grating-bundle sweep
            c<<gf.path.extrude(gf.Path([(xc, s*1.0),(xc-sgn*1.5, s*1.4),(xc-sgn*3.5, s*1.8),(xtip+sgn*2, s*1.97)]),cross_section=xs(0.47))
    return c

if __name__=="__main__":
    comp=stripe_coupler(); out=Path(__file__).parent/"attempt1.gds"; comp.write_gds(str(out)); print(f"wrote {out}")
