"""Parametric device script. Tunables are top-level name = value."""
import json
from pathlib import Path

import gdsfactory as gf

gap = 0.5
length = 18.80685086025288
dy = 4.0
dx = 10.0

c = gf.components.coupler(gap=gap, length=length, dy=dy, dx=dx)
c.write_gds("device.gds", with_metadata=False)

port_widths = [float(port.width) for port in c.ports]
width_um = port_widths[0]
if any(abs(width - width_um) > 1e-9 for width in port_widths):
    raise ValueError(f"Expected uniform port widths, got {port_widths}")

(Path(__file__).resolve().parent / "lengths.json").write_text(
    json.dumps(
        {
            "coupler": {
                "length_um": float(length),
                "gap_um": float(gap),
                "width_um": width_um,
            }
        },
        indent=2,
    )
)
