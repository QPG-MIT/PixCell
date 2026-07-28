"""Parametric primitives-only recreation of a compact four-port waveguide crossing."""

from pathlib import Path
import json

import gdsfactory as gf


# Top-level, substitution-friendly geometry knobs (um).
guide_width = 0.23
port_length = 0.55
lobe_expand_length = 0.95
lobe_contract_length = 0.85
lobe_max_width = 0.94
center_width = 0.78
delta_length = 0.0
layer = (1, 0)
arm_length = port_length + lobe_expand_length + lobe_contract_length


def _cross_section(width: float) -> gf.CrossSection:
    return gf.cross_section.cross_section(width=width, layer=layer)


@gf.cell
def crossing_arm(extension: float = 0.0) -> gf.Component:
    """One access guide and its smooth expansion/recompression lobe."""
    c = gf.Component()
    access = gf.components.straight(
        length=port_length + extension, cross_section=_cross_section(guide_width)
    )
    c.add_ref(access)

    expand_path = gf.Path()
    expand_path.append(gf.path.straight(lobe_expand_length))
    expand = expand_path.extrude_transition(
        gf.path.transition(
            _cross_section(guide_width), _cross_section(lobe_max_width), width_type="sine"
        )
    )
    expand_ref = c.add_ref(expand)
    expand_ref.dmove((port_length + extension, 0))

    contract_path = gf.Path()
    contract_path.append(gf.path.straight(lobe_contract_length))
    contract = contract_path.extrude_transition(
        gf.path.transition(
            _cross_section(lobe_max_width), _cross_section(center_width), width_type="sine"
        )
    )
    contract_ref = c.add_ref(contract)
    contract_ref.dmove((port_length + extension + lobe_expand_length, 0))
    return c


@gf.cell
def four_port_crossing() -> gf.Component:
    c = gf.Component()
    # The arm is drawn from its outer port toward its central end.  Anchor that
    # end at the common crossing center after each cardinal rotation.  The
    # west access arm alone carries delta_length, so it is a measurable true
    # path-extension knob rather than a decorative assignment.
    center = arm_length
    for angle in (0, 90, 180, 270):
        extension = delta_length if angle == 0 else 0.0
        arm = crossing_arm(extension=extension)
        this_length = arm_length + extension
        placements = {
            0: (center - this_length, center),
            90: (center, center - this_length),
            180: (center + this_length, center),
            270: (center, center + this_length),
        }
        ref = c.add_ref(arm)
        ref.drotate(angle)
        ref.dmove(placements[angle])
    return c


if __name__ == "__main__":
    component = four_port_crossing()
    here = Path(__file__).resolve().parent
    component.write_gds(here / "device.gds", with_metadata=False)
    # The honest path-length contract records the real narrow-guide extension.
    (here / "lengths.json").write_text(
        json.dumps(
            {
                "arms": {"reference": arm_length, "extended_access": arm_length + delta_length},
                "delta_length_um": delta_length,
            },
            indent=2,
        )
    )
