"""
cat3 recreation: 1x2 MMI power splitter with tapered access waveguides.

Primitives only (taper + rectangle + straight assembled in a @gf.cell); no
gf.components MMI/coupler stencil. Layer (1,0), gdsfactory 9.20.7.

Topology (see recreation_log.json):
  input single-mode wg --taper up--> [wide multimode region] --two tapers down-->
  two single-mode outputs at the two self-image spots.

Parametric contract: every function knob is a top-level `name = value`. The two
output-arm centerlines are gf.Path objects; on each run the script writes
lengths.json {"arms": {...}, "delta_length_um": ...} derived from those paths.
`delta_length` asymmetrically extends the top output arm (0 -> the symmetric
splitter in the image) and is the spec knob for downstream retargeting.
"""

import json
from pathlib import Path

import gdsfactory as gf

LAYER = (1, 0)

# ---- function knobs (top-level tunables) ------------------------------------
port_width = 0.5        # single-mode access waveguide width (in & out ports), um
in_taper_wide = 1.0     # input taper width at the MMI face, um
in_taper_len = 10.0     # input access taper length, um
mmi_width = 2.5         # multimode region width, um
mmi_length = 5.5        # multimode region length (two-image self-imaging length), um
out_taper_wide = 1.0    # output taper width at the MMI face, um
out_taper_len = 10.0    # output access taper length, um
out_offset = 0.62       # output arm center offset from the optical axis (half separation), um
delta_length = 0.0      # asymmetric top-arm extension, um (spec knob; 0 = symmetric splitter)

_EPS = 1e-9


def device() -> gf.Component:
    c = gf.Component()

    x_mmi_in = in_taper_len
    x_mmi_out = in_taper_len + mmi_length

    # Input access taper: narrow port -> wide, centered on the axis.
    in_taper = c.add_ref(
        gf.components.taper(
            length=in_taper_len, width1=port_width, width2=in_taper_wide, layer=LAYER
        )
    )
    in_taper.movex(0.0)  # spans x in [0, in_taper_len], centered y=0

    # Multimode region: full-width rectangle.
    mmi = c.add_ref(
        gf.components.rectangle(size=(mmi_length, mmi_width), layer=LAYER, centered=False)
    )
    mmi.move((x_mmi_in, -mmi_width / 2.0))

    # Two output access tapers: wide at the MMI face -> narrow port, centers fixed.
    for sign in (+1, -1):
        ot = c.add_ref(
            gf.components.taper(
                length=out_taper_len, width1=out_taper_wide, width2=port_width, layer=LAYER
            )
        )
        ot.move((x_mmi_out, sign * out_offset))

    # Asymmetric extension of the TOP output arm (spec knob): a straight guide
    # segment built as a rectangle primitive (constant width = port_width).
    if delta_length > _EPS:
        ext = c.add_ref(
            gf.components.rectangle(
                size=(delta_length, port_width), layer=LAYER, centered=False
            )
        )
        ext.move((x_mmi_out + out_taper_len, +out_offset - port_width / 2.0))

    return c


def _arm_paths() -> dict[str, gf.Path]:
    """Output-arm centerlines as gf.Path objects (derived, not hand-entered)."""
    x0 = in_taper_len + mmi_length
    x1 = x0 + out_taper_len
    top = gf.Path([(x0, +out_offset), (x1, +out_offset), (x1 + delta_length, +out_offset)])
    bot = gf.Path([(x0, -out_offset), (x1, -out_offset)])
    return {"top": top, "bottom": bot}


def _write_lengths(out_dir: Path) -> None:
    arms = {name: float(p.length()) for name, p in _arm_paths().items()}
    delta = abs(arms["top"] - arms["bottom"])
    (out_dir / "lengths.json").write_text(
        json.dumps({"arms": arms, "delta_length_um": delta}, indent=2)
    )


if __name__ == "__main__":
    out_dir = Path(__file__).resolve().parent
    comp = device()
    comp.flatten()  # single top-level cell -> layer-area/DRC tools see the geometry
    comp.write_gds(str(out_dir / "device.gds"))
    _write_lengths(out_dir)
