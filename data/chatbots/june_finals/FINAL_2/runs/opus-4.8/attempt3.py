"""FINAL_2 attempt 3 (reconstruction): 0.004um strips, keep 1px runs so the
corner specks are captured and the bbox matches the target (else mis-align)."""
import json
from pathlib import Path
import gdsfactory as gf
import numpy as np
from PIL import Image
LAYER=(1,0); dd=Path(__file__).parent.parent.parent
cal=json.loads((dd/"runs/opus-4.8/component/calibration.json").read_text())
black=np.array(Image.open(dd/"device_bw.png").convert("L"))<cal["white_threshold"]
sx,sy=cal["scale_px_per_um"]; x0=cal["bbox"][0]; by1,by2=cal["bbox"][1],cal["bbox"][3]; yc=(by1+by2)/2
xu=lambda p:(p-x0)/sx; ytop=(yc-by1)/sy; step=0.004; ins=0.5/sx
c=gf.Component(); y=ytop
while y> -ytop-1e-9:
    row=int(round(yc-(y-step/2)*sy))
    if 0<=row<black.shape[0]:
        r=black[row,:]; rr=[]; s=None
        for i,v in enumerate(r):
            if v and s is None: s=i
            elif not v and s is not None: rr.append((s,i-1)); s=None
        if s is not None: rr.append((s,len(r)-1))
        for a,b in rr:
            xa,xb=xu(a)+ins,xu(b+1)-ins; w=round(xb-xa,4)
            if w>0:
                t=c<<gf.components.rectangle(size=(w,round(step,4)),layer=LAYER); t.move((round(xa,4),round(y-step,4)))
    y-=step
if __name__=="__main__":
    out=Path(__file__).parent/"attempt3.gds"; c.write_gds(str(out)); print(f"wrote {out}")
