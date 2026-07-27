"""FINAL_2 attempt 2 (parametric). Fix vs a1 (0.444):
- a1's bbox was 19.46x8.3 not 25x10, so the renderer (left-align x, center y) shifted
  everything. The target's bbox is set by tiny edge specks at (0,-5), (3.68,+5), (25,-3).
- add anchors at those exact specks so my bbox == target bbox -> correct alignment.
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
        vtaper(c,cx,1.0,3.0,2.00,1.24); vtaper(c,cx,3.0,4.85,1.24,1.24)
    vtaper(c,12.48,-3.45,-2.34,0.30,2.40)
    # bbox-anchor specks (present in the target image)
    rect(c,0.0,-5.0,0.06,-4.98)
    rect(c,3.66,4.98,3.72,5.0)
    rect(c,24.94,-3.56,25.0,-2.52)
    return c

if __name__=="__main__":
    comp=mmi_1x4(); out=Path(__file__).parent/"attempt2.gds"; comp.write_gds(str(out)); print(f"wrote {out}")
