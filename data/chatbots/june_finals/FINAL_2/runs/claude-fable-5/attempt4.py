"""FINAL_2 attempt 4 (reconstruction tier): 3nm strips + frame-speck anchors."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "_tools"))
from strips_003 import STRIPS
from strips_to_gds import build
import gdsfactory as gf

LAYER = (1, 0)

if __name__ == "__main__":
    component = build(STRIPS + [
        (4.996, 4.986, 3.66, 3.70),     # top edge speck
        (-4.986, -4.996, 0.0, 0.06),    # bottom-left corner speck
        (-2.52, -2.56, 24.99, 25.0),    # right edge dash
    ])
    out = Path(__file__).parent / "attempt4.gds"
    component.write_gds(str(out))
    print(f"wrote {out}")
