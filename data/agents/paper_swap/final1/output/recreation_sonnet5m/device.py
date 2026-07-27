"""Adiabatic 3-waveguide directional coupler (ADC) 1x2 power splitter.

Primitives-only parametric recreation of experiments/paper_swap/final1/device_bw.png.
"""

import gdsfactory as gf

LAYER = (1, 0)

# --- parametric contract: top-level tunables (function-defining knobs) ---
lead_in_length = 3.5
coupling_length = 21.6
sbend_length = 11.4
sbend_dy = 0.46
leadout_length = 3.5

bus_width_in = 0.268
tip_width = 0.070
arm_width_full = 0.240
arm_offset = 0.265


@gf.cell
def adc_splitter(
    lead_in_length: float = lead_in_length,
    coupling_length: float = coupling_length,
    sbend_length: float = sbend_length,
    sbend_dy: float = sbend_dy,
    leadout_length: float = leadout_length,
    bus_width_in: float = bus_width_in,
    tip_width: float = tip_width,
    arm_width_full: float = arm_width_full,
    arm_offset: float = arm_offset,
) -> gf.Component:
    c = gf.Component()

    xs_bus_in = gf.cross_section.cross_section(width=bus_width_in, layer=LAYER)
    xs_arm_full = gf.cross_section.cross_section(width=arm_width_full, layer=LAYER)

    # central bus waveguide: straight lead-in, then adiabatic taper down to a tip
    bus_lead = c << gf.components.straight(length=lead_in_length, cross_section=xs_bus_in)
    bus_taper = c << gf.components.taper(
        length=coupling_length, width1=bus_width_in, width2=tip_width, layer=LAYER
    )
    bus_taper.connect("o1", bus_lead.ports["o2"])

    # top arm: tip -> full-width adiabatic taper, then S-bend out, then leadout
    top_taper = c << gf.components.taper(
        length=coupling_length, width1=tip_width, width2=arm_width_full, layer=LAYER
    )
    top_taper.move((lead_in_length, arm_offset))
    top_sbend = c << gf.components.bend_s(size=(sbend_length, sbend_dy), cross_section=xs_arm_full)
    top_sbend.connect("o1", top_taper.ports["o2"])
    top_leadout = c << gf.components.straight(length=leadout_length, cross_section=xs_arm_full)
    top_leadout.connect("o1", top_sbend.ports["o2"])

    # bottom arm: mirror of top arm
    bot_taper = c << gf.components.taper(
        length=coupling_length, width1=tip_width, width2=arm_width_full, layer=LAYER
    )
    bot_taper.move((lead_in_length, -arm_offset))
    bot_sbend = c << gf.components.bend_s(size=(sbend_length, -sbend_dy), cross_section=xs_arm_full)
    bot_sbend.connect("o1", bot_taper.ports["o2"])
    bot_leadout = c << gf.components.straight(length=leadout_length, cross_section=xs_arm_full)
    bot_leadout.connect("o1", bot_sbend.ports["o2"])

    c.add_port("o1", port=bus_lead.ports["o1"])
    c.add_port("o2", port=top_leadout.ports["o2"])
    c.add_port("o3", port=bot_leadout.ports["o2"])

    return c


if __name__ == "__main__":
    comp = adc_splitter()
    comp.write_gds("device.gds")
