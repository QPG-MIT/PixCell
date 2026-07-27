"""FINAL_7 attempt 2 (parametric). Fixes vs a1 (0.599):
- ring = uniform-width 0.52 racetrack, centerline x[0.26,2.74] y[+/-2.49] rx/ry 0.64 (outer reaches +/-2.75)
- removed thick central wedges (they filled the lens -> red diamond); vertices sit on the ring wall
- bars = hollow frames x[1.05,1.94] y[+/-(0.39..1.43)] minus two windows (leaves central post)
- 4 arms meet at vertices (0.518,0)/(2.476,0), forming the '<>' lens points
"""
import math
from pathlib import Path
import gdsfactory as gf

LAYER=(1,0)
def xs(w): return gf.cross_section.cross_section(width=w, layer=LAYER, radius=1.0, radius_min=0.02)
def rect(c,x1,y1,x2,y2):
    r=c<<gf.components.rectangle(size=(round(x2-x1,4),round(y2-y1,4)),layer=LAYER); r.move((round(x1,4),round(y1,4))); return r

def racetrack(x1,x2,y1,y2,rx,ry,n=30):
    cx1,cx2=x1+rx,x2-rx; cy1,cy2=y1+ry,y2-ry; p=[(cx1,y2),(cx2,y2)]
    for i in range(1,n+1): t=math.pi/2*(1-i/n); p.append((cx2+rx*math.cos(t),cy2+ry*math.sin(t)))
    p.append((x2,cy1))
    for i in range(1,n+1): t=-math.pi/2*(i/n); p.append((cx2+rx*math.cos(t),cy1+ry*math.sin(t)))
    p.append((cx1,y1))
    for i in range(1,n+1): t=-math.pi/2*(1+i/n); p.append((cx1+rx*math.cos(t),cy1+ry*math.sin(t)))
    p.append((x1,cy2))
    for i in range(1,n+1): t=math.pi/2*(2-i/n); p.append((cx1+rx*math.cos(t),cy2+ry*math.sin(t)))
    p.append((cx1,y2)); return p

@gf.cell
def stadium_mzi() -> gf.Component:
    c=gf.Component()
    c<<gf.path.extrude(gf.Path(racetrack(0.26,2.74,-2.49,2.49,0.64,0.64)),cross_section=xs(0.52))
    for s in (1,-1):
        yo1,yo2=(0.39,1.43) if s>0 else (-1.43,-0.39)
        frame=gf.components.rectangle(size=(0.89,1.04),layer=LAYER)
        win=gf.Component()
        w1=win<<gf.components.rectangle(size=(0.32,0.55),layer=LAYER); w1.move((0.07,0.24))
        w2=win<<gf.components.rectangle(size=(0.32,0.55),layer=LAYER); w2.move((0.50,0.24))
        bar=gf.boolean(frame,win,"not",layer=LAYER); b=c<<bar; b.move((1.05,yo1))
        # arms from the two vertices to this bar
        c<<gf.path.extrude(gf.Path([(0.518,0.0),(0.72,s*0.72),(1.00,s*0.90),(1.20,s*0.90)]),cross_section=xs(0.46))
        c<<gf.path.extrude(gf.Path([(2.476,0.0),(2.27,s*0.72),(1.99,s*0.90),(1.79,s*0.90)]),cross_section=xs(0.46))
    return c

if __name__=="__main__":
    comp=stadium_mzi(); out=Path(__file__).parent/"attempt2.gds"; comp.write_gds(str(out)); print(f"wrote {out}")
