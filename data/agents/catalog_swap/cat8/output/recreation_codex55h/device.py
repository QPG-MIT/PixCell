from __future__ import annotations

import json
from pathlib import Path

import gdsfactory as gf


layer = (1, 0)

# Function-defining top-level tunables, in microns.
delta_length = 6.38
core_width_um = 0.452
rib_width_um = 0.55
period_um = 0.3177520628554522
rib_length_um = 0.16298688319800123
lead_gap_um = 0.16737039350405997
rib_count = 20

gds_filename = "device.gds"


@gf.cell
def corrugated_waveguide() -> gf.Component:
    c = gf.Component()

    spine_path = gf.path.straight(length=delta_length)
    spine = spine_path.extrude(layer=layer, width=core_width_um)
    c << spine

    rib = gf.components.rectangle(
        size=(rib_length_um, rib_width_um),
        layer=layer,
        centered=False,
        port_type=None,
    )
    for index in range(rib_count):
        x = lead_gap_um + index * period_um
        ref = c << rib
        ref.dmove((x, -rib_width_um / 2))

    c.info["spine_length_um"] = spine_path.length()
    return c


def main() -> None:
    component = corrugated_waveguide().copy()
    component.flatten()
    out_dir = Path(__file__).resolve().parent
    component.write_gds(out_dir / gds_filename, with_metadata=False)

    spine_path = gf.path.straight(length=delta_length)
    lengths = {
        "arms": {"reference": 0.0, "spine": spine_path.length()},
        "delta_length_um": spine_path.length(),
    }
    (out_dir / "lengths.json").write_text(json.dumps(lengths, indent=2) + "\n")


if __name__ == "__main__":
    main()
