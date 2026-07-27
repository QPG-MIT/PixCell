"""Build the opening figure pair with exact GDS geometry and Wolfram layout.

GDSFactory constructs every device body.  The Wolfram script is only the
vector compositor: it controls typography, annotation, panel layout, and
shallow illustrative relief.  The x-y geometry is never redrawn or rescaled
transversely.

Run:
    .venv/bin/python arxiv/scripts/build_fig_vocabulary_wolfram.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
TOOLS = Path(__file__).resolve().parent
GEOMETRY_JSON = REPO / "tmp" / "pdfs" / "fig-vocabulary-geometry.json"
OUTPUT_DIRECTORY = REPO / "arxiv" / "figures"


def main() -> None:
    wolframscript = shutil.which("wolframscript")
    if wolframscript is None:
        raise RuntimeError("wolframscript is required to build these figures")

    subprocess.run(
        [
            sys.executable,
            str(TOOLS / "export_fig_vocabulary_geometry.py"),
            str(GEOMETRY_JSON),
        ],
        cwd=REPO,
        check=True,
    )
    subprocess.run(
        [
            wolframscript,
            "-file",
            str(TOOLS / "compose_fig_vocabulary.wls"),
            str(GEOMETRY_JSON),
            str(OUTPUT_DIRECTORY),
        ],
        cwd=REPO,
        check=True,
    )


if __name__ == "__main__":
    main()
