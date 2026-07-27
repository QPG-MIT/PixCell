"""FINAL_5: contra-directional grating coupler (18.24 x 0.7 um). Attempt 1 (parametric).

Independent measurement (Opus 4.8). Five horizontal layers:
  top rail  y[+0.280,+0.348]  | top comb  y[+0.036,+0.088] (teeth p0.15 w0.12)
  center bus y[-0.007,+0.020] | bot comb  y[-0.074,-0.023] (teeth p0.16 w0.12)
  bot rail  y[-0.332,-0.266]
Plus entry diagonal (top-left -> top comb), exit diagonal (bot comb -> bot-right),
and two hairpin U-turns (top rail<->top comb at right; bot rail<->bot comb at left).
"""
from pathlib import Path
import gdsfactory as gf

LAYER = (1, 0)

def xs(w): return gf.cross_section.cross_section(width=w, layer=LAYER, radius=2.0, radius_min=0.02)

def rect(c, x1, y1, x2, y2):
    r = c << gf.components.rectangle(size=(round(x2-x1,4), round(y2-y1,4)), layer=LAYER)
    r.move((round(x1,4), round(y1,4)))
    return r

@gf.cell
def contra_grating() -> gf.Component:
    c = gf.Component()
    # center bus
    rect(c, 1.94, -0.007, 15.97, 0.020)
    # top rail
    rect(c, 2.0, 0.280, 14.8, 0.348)
    # top comb: solid ends + teeth
    rect(c, 1.97, 0.036, 4.45, 0.088)
    rect(c, 13.17, 0.036, 14.82, 0.088)
    x = 4.45
    while x < 13.17:
        rect(c, x, 0.036, x+0.12, 0.088); x += 0.15
    # bottom rail
    rect(c, 3.3, -0.332, 15.0, -0.266)
    # bottom comb: solid ends + teeth
    rect(c, 3.5, -0.074, 4.45, -0.023)
    rect(c, 13.16, -0.074, 15.5, -0.023)
    x = 4.45
    while x < 13.16:
        rect(c, x, -0.074, x+0.12, -0.023); x += 0.16
    # entry diagonal (top-left -> top comb left)
    c << gf.path.extrude(gf.Path([(0.0,0.330),(0.45,0.235),(0.95,0.145),(1.45,0.105),(1.95,0.082)]), cross_section=xs(0.040))
    # exit diagonal (bot comb right -> bottom-right point)
    c << gf.path.extrude(gf.Path([(15.5,-0.060),(16.1,-0.081),(16.7,-0.122),(17.3,-0.209),(17.9,-0.310)]), cross_section=xs(0.040))
    # right hairpin: top rail -> top comb (bulge right)
    c << gf.path.extrude(gf.Path([(14.6,0.314),(15.15,0.255),(15.40,0.190),(15.15,0.110),(14.6,0.062)]), cross_section=xs(0.066))
    # left hairpin: bottom rail -> bottom comb (bulge left)
    c << gf.path.extrude(gf.Path([(3.5,-0.299),(2.85,-0.240),(2.55,-0.170),(2.85,-0.095),(3.5,-0.049)]), cross_section=xs(0.064))
    return c

if __name__ == "__main__":
    comp = contra_grating()
    out = Path(__file__).parent / "attempt1.gds"
    comp.write_gds(str(out)); print(f"wrote {out}")
