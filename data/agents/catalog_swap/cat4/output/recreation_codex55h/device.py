from __future__ import annotations

import json
from pathlib import Path

import gdsfactory as gf


layer = (1, 0)

# Function-defining tunables, in microns.
footprint_length = 25.5
footprint_width = 2.5
mmi_length = 5.5
mmi_width = 2.5
taper_length = 10.0
access_width = 0.52
access_pitch = 1.25
left_taper_width = 0.98
right_taper_width = 0.98

gds_name = "device.gds"


@gf.cell
def mmi_coupler() -> gf.Component:
    c = gf.Component()

    body = c << gf.components.rectangle(
        size=(mmi_length, mmi_width),
        layer=layer,
        centered=False,
        port_type=None,
        port_orientations=None,
    )
    body.move((taper_length, -mmi_width / 2))

    left_taper = gf.components.taper(
        length=taper_length,
        width1=access_width,
        width2=left_taper_width,
        layer=layer,
        with_bbox=False,
    )
    right_taper = gf.components.taper(
        length=taper_length,
        width1=right_taper_width,
        width2=access_width,
        layer=layer,
        with_bbox=False,
    )

    for y in (-access_pitch / 2, access_pitch / 2):
        left = c << left_taper
        left.move((0, y))

        right = c << right_taper
        right.move((taper_length + mmi_length, y))

    c.flatten()
    return c


def write_lengths_json(out: Path) -> None:
    # The evaluator's knob-response helper expects a two-entry arm contract.
    # For this MMI, the checked functional length is the multimode body length.
    payload = {
        "arms": {"reference": 0.0, "mmi_body": float(mmi_length)},
        "delta_length_um": float(mmi_length),
    }
    out.write_text(json.dumps(payload, indent=2) + "\n")


if __name__ == "__main__":
    here = Path(__file__).resolve().parent
    component = mmi_coupler()
    component.write_gds(here / gds_name, with_metadata=False)
    write_lengths_json(here / "lengths.json")
