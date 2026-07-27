"""FINAL_8 attempt 2 (parametric). Fixes vs a1 (0.922):
- sweep tips capped at centerline y=1.75 so band top reaches exactly 2.0 (a1 overshot -> 4.384 tall -> shrink-fit)
- sweep waypoints fit to measured band centerlines (slab band + grating-bundle band per corner)
"""
from pathlib import Path
import gdsfactory as gf

LAYER=(1,0)
def xs(w): return gf.cross_section.cross_section(width=w, layer=LAYER, radius=3.0, radius_min=0.05)
def rect(c,x1,y1,x2,y2):
    r=c<<gf.components.rectangle(size=(round(x2-x1,4),round(y2-y1,4)),layer=LAYER); r.move((round(x1,4),round(y1,4))); return r

CENTER=[(0.160,0.230),(0.060,0.130),(-0.037,0.024),(-0.138,-0.074),(-0.243,-0.173)]
TOPSTRIPES=[(0.768,0.836),(0.868,0.936),(0.969,1.036),(1.068,1.136),(1.168,1.236)]
# centerline waypoints for the left-corner sweeps (x descending toward the tip)
SLAB_SWEEP=[(11.0,0.50),(9.0,0.80),(7.0,1.05),(5.8,1.40),(5.2,1.74)]
BUND_SWEEP=[(10.5,1.00),(9.0,1.20),(7.9,1.55),(7.3,1.74)]

@gf.cell
def stripe_coupler() -> gf.Component:
    c=gf.Component()
    for y1,y2 in CENTER: rect(c,0.0,y1,120.0,y2)
    for s in (1,-1):
        rect(c,11.0,(0.267 if s>0 else -0.738),109.0,(0.738 if s>0 else -0.267))
        for y1,y2 in TOPSTRIPES:
            rect(c,11.0,(y1 if s>0 else -y2),109.0,(y2 if s>0 else -y1))
        for mirror in (False,True):
            for sweep in (SLAB_SWEEP,BUND_SWEEP):
                pts=[((120.0-x) if mirror else x, s*y) for x,y in sweep]
                c<<gf.path.extrude(gf.Path(pts),cross_section=xs(0.47))
    return c

if __name__=="__main__":
    comp=stripe_coupler(); out=Path(__file__).parent/"attempt2.gds"; comp.write_gds(str(out)); print(f"wrote {out}")
