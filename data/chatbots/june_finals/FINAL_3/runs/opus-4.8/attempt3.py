"""FINAL_3 attempt 3 (reconstruction): 5nm strip trace."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "_tools_opus"))
from recon import main
if __name__=="__main__":
    main(Path(__file__).parent.parent.parent, 0.005, Path(__file__).parent/"attempt3.gds", inset=0.5)
