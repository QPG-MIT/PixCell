"""FINAL_3: asymmetric directional coupler (120 x 4 um). Attempt 1 (parametric).

Independent measurement (Opus 4.8). Two waveguides, each: entry straight ->
S-bend into a central coupling straight -> S-bend -> exit straight.
Top guide y +1.74 -> +0.22 -> +1.83 (w~0.34); bottom y -1.71 -> -0.24 -> -1.83 (w~0.27).
"""
from pathlib import Path
import gdsfactory as gf

LAYER=(1,0)
def xs(w): return gf.cross_section.cross_section(width=w, layer=LAYER, radius=8.0, radius_min=0.1)

TOP=[(0,1.740),(15,1.740),(19,1.700),(22,1.520),(25,1.00),(28,0.47),(31,0.30),(35,0.225),
     (88,0.220),(92,0.55),(95,1.05),(98,1.64),(101,1.79),(104,1.825),(120,1.835)]
BOT=[(0,-1.710),(15,-1.710),(19,-1.680),(22,-1.55),(25,-1.00),(28,-0.45),(31,-0.30),(35,-0.245),
     (88,-0.240),(92,-0.52),(95,-1.05),(98,-1.63),(101,-1.79),(104,-1.825),(120,-1.835)]

@gf.cell
def dc() -> gf.Component:
    c=gf.Component()
    c<<gf.path.extrude(gf.Path(TOP),cross_section=xs(0.34))
    c<<gf.path.extrude(gf.Path(BOT),cross_section=xs(0.27))
    return c

if __name__=="__main__":
    comp=dc(); out=Path(__file__).parent/"attempt1.gds"; comp.write_gds(str(out)); print(f"wrote {out}")
