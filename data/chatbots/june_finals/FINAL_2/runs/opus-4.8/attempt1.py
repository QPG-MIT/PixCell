"""FINAL_2: 1x4 MMI splitter (25 x 10 um). Attempt 1 (parametric).

Independent measurement (Opus 4.8).
- solid body rect x[2.76,22.22] y[-2.34,1.42]
- 4 top output ports at x-centers 5.44/9.62/15.03/19.49: taper 2.0->1.24 (y1.0->3.0)
  then straight 1.24 up to y~4.85
- 1 bottom input: inverse taper 2.4 -> point, center x12.48, down to y-3.45
"""
from pathlib import Path
import gdsfactory as gf

LAYER=(1,0)
PORTS=[5.44,9.62,15.03,19.49]
def rect(c,x1,y1,x2,y2):
    r=c<<gf.components.rectangle(size=(round(x2-x1,4),round(y2-y1,4)),layer=LAYER); r.move((round(x1,4),round(y1,4))); return r
def vtaper(c,cx,yb,yt,wb,wt):
    t=c<<gf.components.taper(length=round(yt-yb,4),width1=wb,width2=wt,layer=LAYER); t.rotate(90); t.move((cx,yb)); return t

@gf.cell
def mmi_1x4() -> gf.Component:
    c=gf.Component()
    rect(c,2.76,-2.34,22.22,1.42)
    for cx in PORTS:
        vtaper(c,cx,1.0,3.0,2.00,1.24)        # widening base taper
        vtaper(c,cx,3.0,4.85,1.24,1.24)        # thin straight tip
    vtaper(c,12.48,-3.45,-2.34,0.30,2.40)      # bottom input taper to point
    return c

if __name__=="__main__":
    comp=mmi_1x4(); out=Path(__file__).parent/"attempt1.gds"; comp.write_gds(str(out)); print(f"wrote {out}")
