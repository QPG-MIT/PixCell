"""FINAL_1: 1x2 trident splitter (40 x 1.7 um). Attempt 1 (parametric).

Independent measurement (Opus 4.8).
- center: straight w0.274 x[0,3] @y+0.015, then taper 0.270->0.04 to a point @x~25.5
- top arm: taper 0.066->0.244 x[3.5,26] @y+0.281, S-bend up to +0.730 (x[26,36]), straight to x40
- bottom arm mirrors about y~+0.01 (out at -0.728)
"""
from pathlib import Path
import gdsfactory as gf

LAYER=(1,0)
def xs(w): return gf.cross_section.cross_section(width=w, layer=LAYER, radius=4.0, radius_min=0.05)
def place(c,comp,x,y):
    r=c<<comp; r.move((x,y)); return r

@gf.cell
def trident() -> gf.Component:
    c=gf.Component()
    # center
    place(c,gf.components.straight(length=3.0,cross_section=xs(0.274)),0.0,0.015)
    place(c,gf.components.taper(length=22.5,width1=0.270,width2=0.040,layer=LAYER),3.0,0.015)
    for s in (1,-1):
        cy = 0.281 if s>0 else -0.259
        oy = 0.730 if s>0 else -0.728
        place(c,gf.components.taper(length=22.5,width1=0.066,width2=0.244,layer=LAYER),3.5,cy)
        b=place(c,gf.components.bend_s(size=(10.0, round(oy-cy,3)),cross_section=xs(0.244)),26.0,cy)
        place(c,gf.components.straight(length=4.0,cross_section=xs(0.244)),36.0,oy)
    return c

if __name__=="__main__":
    comp=trident(); out=Path(__file__).parent/"attempt1.gds"; comp.write_gds(str(out)); print(f"wrote {out}")
