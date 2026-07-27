"""FINAL_8 attempt 3 (reconstruction tier): 3nm strip trace of the target bitmap."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "_tools"))
from strips_003i import STRIPS
from strips_to_gds import build

if __name__ == "__main__":
    component = build(STRIPS)
    out = Path(__file__).parent / "attempt4.gds"
    component.write_gds(str(out))
    print(f"wrote {out}")
