"""FINAL_1 attempt 4 (reconstruction): 2nm strips + 0.35px inset."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "_tools_opus"))
from recon import main
if __name__=="__main__":
    main(Path(__file__).parent.parent.parent, 0.002, Path(__file__).parent/"attempt4.gds", inset=0.35)
