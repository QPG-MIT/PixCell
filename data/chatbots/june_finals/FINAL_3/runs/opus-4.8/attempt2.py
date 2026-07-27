"""FINAL_3 attempt 2 (parametric). Fixes vs a1 (0.756, recall 0.80):
- denser centerline waypoints fit to the measured S-bend shoulders
- wider guides (top 0.40, bottom 0.31) to recover the missing shoulder area
  (target guides widen to ~0.6 at the bend shoulders; constant width is a compromise)
"""
from pathlib import Path
import gdsfactory as gf

LAYER=(1,0)
def xs(w): return gf.cross_section.cross_section(width=w, layer=LAYER, radius=8.0, radius_min=0.1)

TOP=[(0,1.737),(10,1.737),(15,1.735),(18,1.719),(21,1.62),(24,1.20),(27,0.60),(30,0.32),(34,0.225),
     (40,0.219),(78,0.219),(86,0.235),(90,0.40),(93,0.75),(96,1.25),(99,1.70),(102,1.813),(106,1.828),(120,1.835)]
BOT=[(0,-1.708),(10,-1.711),(15,-1.713),(18,-1.700),(21,-1.60),(24,-1.18),(27,-0.58),(30,-0.32),(34,-0.245),
     (40,-0.240),(78,-0.241),(86,-0.255),(90,-0.42),(93,-0.78),(96,-1.28),(99,-1.70),(102,-1.815),(106,-1.828),(120,-1.832)]

@gf.cell
def dc() -> gf.Component:
    c=gf.Component()
    c<<gf.path.extrude(gf.Path(TOP),cross_section=xs(0.40))
    c<<gf.path.extrude(gf.Path(BOT),cross_section=xs(0.31))
    return c

if __name__=="__main__":
    comp=dc(); out=Path(__file__).parent/"attempt2.gds"; comp.write_gds(str(out)); print(f"wrote {out}")
