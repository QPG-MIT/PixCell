"""FINAL_2 attempt 3 (reconstruction tier): 5nm strip trace of the target bitmap."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "_tools"))
from strips_005 import STRIPS
from strips_to_gds import build

if __name__ == "__main__":
    component = build(STRIPS)
    out = Path(__file__).parent / "attempt3.gds"
    component.write_gds(str(out))
    print(f"wrote {out}")
