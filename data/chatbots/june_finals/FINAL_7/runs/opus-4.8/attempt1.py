"""FINAL_7: stadium ring + MZI (3 x 5.5 um). Attempt 1 (parametric).

Independent measurement (Opus 4.8). Double mirror symmetry.
- outer stadium ring: racetrack centerline x[0.28,2.72] y[+/-2.38] extruded w~0.55
- two slotted bars: frame x[1.05,1.94] y[+/-(0.39..1.43)] with a central post + two windows
- four diagonal arms from bar ends to central vertices (0.52,0)&(2.48,0)
- two horizontal wedges joining the vertices to the ring side walls
"""
import math
from pathlib import Path
import gdsfactory as gf

LAYER=(1,0)
def xs(w): return gf.cross_section.cross_section(width=w, layer=LAYER, radius=1.0, radius_min=0.02)
def rect(c,x1,y1,x2,y2):
    r=c<<gf.components.rectangle(size=(round(x2-x1,4),round(y2-y1,4)),layer=LAYER); r.move((round(x1,4),round(y1,4))); return r

def racetrack(x1,x2,y1,y2,rx,ry,n=28):
    cx1,cx2=x1+rx,x2-rx; cy1,cy2=y1+ry,y2-ry; p=[]
    p.append((cx1,y2)); p.append((cx2,y2))
    for i in range(1,n+1): t=math.pi/2*(1-i/n); p.append((cx2+rx*math.cos(t),cy2+ry*math.sin(t)))
    p.append((x2,cy1))
    for i in range(1,n+1): t=-math.pi/2*(i/n); p.append((cx2+rx*math.cos(t),cy1+ry*math.sin(t)))
    p.append((cx1,y1))
    for i in range(1,n+1): t=-math.pi/2*(1+i/n); p.append((cx1+rx*math.cos(t),cy1+ry*math.sin(t)))
    p.append((x1,cy2))
    for i in range(1,n+1): t=math.pi/2*(2-i/n); p.append((cx1+rx*math.cos(t),cy2+ry*math.sin(t)))
    p.append((cx1,y2))
    return p

def slotted_bar(c, y_sign):
    yo1,yo2 = 0.39, 1.43
    fr=gf.Component()
    rect(fr,1.05,yo1,1.94,yo2)
    bar=c<<fr
    # windows
    w1=gf.components.rectangle(size=(0.30,0.66),layer=LAYER)
    h1=c<<w1; h1.move((1.12,0.58))
    h2=c<<gf.components.rectangle(size=(0.30,0.66),layer=LAYER); h2.move((1.57,0.58))
    if y_sign<0:
        for ref in (bar,h1,h2): ref.mirror_y(0.0)
    return

@gf.cell
def stadium_mzi() -> gf.Component:
    c=gf.Component()
    # outer ring
    c<<gf.path.extrude(gf.Path(racetrack(0.28,2.72,-2.38,2.38,0.62,0.62)),cross_section=xs(0.55))
    # slotted bars top & bottom: build frame then cut windows via boolean
    for s in (1,-1):
        yo1,yo2=(0.39,1.43) if s>0 else (-1.43,-0.39)
        frame=gf.components.rectangle(size=(0.89,1.04),layer=LAYER)
        win=gf.Component(); 
        w1=win<<gf.components.rectangle(size=(0.30,0.66),layer=LAYER); w1.move((0.10,0.19))
        w2=win<<gf.components.rectangle(size=(0.30,0.66),layer=LAYER); w2.move((0.52,0.19))
        bar=gf.boolean(frame,win,"not",layer=LAYER)
        b=c<<bar; b.move((1.05,yo1))
        # diagonal arms to vertices
        c<<gf.path.extrude(gf.Path([(0.52,0.0),(0.82,s*0.45),(1.05,s*0.70)]),cross_section=xs(0.50))
        c<<gf.path.extrude(gf.Path([(2.48,0.0),(2.18,s*0.45),(1.94,s*0.70)]),cross_section=xs(0.50))
    # horizontal wedges joining vertices to ring inner walls
    c<<gf.path.extrude(gf.Path([(0.30,0.0),(0.52,0.0)]),cross_section=xs(0.78))
    c<<gf.path.extrude(gf.Path([(2.48,0.0),(2.70,0.0)]),cross_section=xs(0.78))
    return c

if __name__=="__main__":
    comp=stadium_mzi(); out=Path(__file__).parent/"attempt1.gds"; comp.write_gds(str(out)); print(f"wrote {out}")
