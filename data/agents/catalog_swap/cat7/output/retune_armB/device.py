"""Parametric device script. Tunables are top-level name = value."""
import json
from pathlib import Path

import gdsfactory as gf

length = 94.57869698106396
spacing = 1.56
n_loops = 12

c = gf.components.spiral(length=length, spacing=spacing, n_loops=n_loops)
c.write_gds("device.gds", with_metadata=False)

Path("lengths.json").write_text(
    json.dumps({"path": {"total_um": float(c.info["length"])}}, indent=2)
)
