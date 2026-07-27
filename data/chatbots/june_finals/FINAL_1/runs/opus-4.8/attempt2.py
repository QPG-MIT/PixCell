"""FINAL_1 attempt 2 (parametric). Fixes vs a1 (0.952):
- S-bends rebuilt as paths through measured centerline waypoints (bend_s bezier was slightly off)
- arm tapers start at the true tip x3.2; center taper tip extended/narrowed
"""
from pathlib import Path
import gdsfactory as gf

LAYER=(1,0)
def xs(w): return gf.cross_section.cross_section(width=w, layer=LAYER, radius=4.0, radius_min=0.05)
def place(c,comp,x,y):
    r=c<<comp; r.move((x,y)); return r

TOPB=[(26,0.280),(28,0.316),(30,0.433),(32,0.596),(34,0.702),(35,0.722),(36,0.730),(40,0.730)]
BOTB=[(26,-0.251),(28,-0.285),(30,-0.405),(32,-0.575),(34,-0.687),(35,-0.715),(36,-0.728),(40,-0.728)]

@gf.cell
def trident() -> gf.Component:
    c=gf.Component()
    place(c,gf.components.straight(length=3.0,cross_section=xs(0.274)),0.0,0.015)
    place(c,gf.components.taper(length=22.6,width1=0.270,width2=0.030,layer=LAYER),3.0,0.015)
    place(c,gf.components.taper(length=22.8,width1=0.050,width2=0.244,layer=LAYER),3.2,0.281)
    place(c,gf.components.taper(length=22.8,width1=0.050,width2=0.244,layer=LAYER),3.2,-0.259)
    c<<gf.path.extrude(gf.Path(TOPB),cross_section=xs(0.244))
    c<<gf.path.extrude(gf.Path(BOTB),cross_section=xs(0.244))
    return c

if __name__=="__main__":
    comp=trident(); out=Path(__file__).parent/"attempt2.gds"; comp.write_gds(str(out)); print(f"wrote {out}")
