"""Contra-directional grating coupler with U-bend waveguides."""
import gdsfactory as gf
import numpy as np

# === FUNCTION-DEFINING TUNABLES ===
waveguide_width_um = 0.7
coupling_length_um = 9.2
grating_period_um = 0.14
grating_tooth_width_um = 0.04
gap_um = 0.10
bend_radius_um = 0.85
taper_length_um = 2.2
taper_tip_width_um = 0.05

layer = (1, 0)


@gf.cell
def contra_dc_grating() -> gf.Component:
    c = gf.Component()

    arc_span = np.pi * bend_radius_um
    y_coupling = waveguide_width_um / 2 + gap_um + waveguide_width_um / 2
    y_taper = y_coupling + 2 * bend_radius_um

    # ===== Central bus =====
    bus = c << gf.components.rectangle(size=(coupling_length_um, waveguide_width_um), layer=layer)
    bus.move((-coupling_length_um / 2, -waveguide_width_um / 2))

    # ===== Grating teeth =====
    num_teeth = int(coupling_length_um / grating_period_um)
    for i in range(num_teeth):
        x = -coupling_length_um / 2 + grating_period_um / 2 + i * grating_period_um
        tooth_top = c << gf.components.rectangle(size=(grating_tooth_width_um, gap_um), layer=layer)
        tooth_top.move((x - grating_tooth_width_um / 2, waveguide_width_um / 2))
        tooth_bot = c << gf.components.rectangle(size=(grating_tooth_width_um, gap_um), layer=layer)
        tooth_bot.move((x - grating_tooth_width_um / 2, -waveguide_width_um / 2 - gap_um))

    # ===== Upper coupling waveguide =====
    upper_coupling = c << gf.components.rectangle(
        size=(coupling_length_um, waveguide_width_um), layer=layer)
    upper_coupling.move((-coupling_length_um / 2, y_coupling - waveguide_width_um / 2))

    # ===== Lower coupling waveguide =====
    lower_coupling = c << gf.components.rectangle(
        size=(coupling_length_um, waveguide_width_um), layer=layer)
    lower_coupling.move((-coupling_length_um / 2, -y_coupling - waveguide_width_um / 2))

    # ===== Upper left 180° bend =====
    upper_left_arc_path = gf.path.arc(radius=bend_radius_um, angle=-180)
    upper_left_arc = c << gf.path.extrude(upper_left_arc_path, width=waveguide_width_um, layer=layer)
    upper_left_arc.move((-coupling_length_um / 2, y_taper))

    # ===== Upper right 180° bend =====
    upper_right_arc_path = gf.path.arc(radius=bend_radius_um, angle=180)
    upper_right_arc = c << gf.path.extrude(upper_right_arc_path, width=waveguide_width_um, layer=layer)
    upper_right_arc.move((coupling_length_um / 2, y_coupling))

    # ===== Upper tapers =====
    upper_taper_left = c << gf.components.taper(
        length=taper_length_um, width1=taper_tip_width_um, width2=waveguide_width_um, layer=layer)
    upper_taper_left.move((-coupling_length_um / 2 - arc_span - taper_length_um, y_taper - waveguide_width_um / 2))

    upper_taper_right = c << gf.components.taper(
        length=taper_length_um, width1=waveguide_width_um, width2=taper_tip_width_um, layer=layer)
    upper_taper_right.move((coupling_length_um / 2 + arc_span, y_taper - waveguide_width_um / 2))

    # ===== Lower left 180° bend =====
    lower_left_arc_path = gf.path.arc(radius=bend_radius_um, angle=180)
    lower_left_arc = c << gf.path.extrude(lower_left_arc_path, width=waveguide_width_um, layer=layer)
    lower_left_arc.move((-coupling_length_um / 2, -y_taper))

    # ===== Lower right 180° bend =====
    lower_right_arc_path = gf.path.arc(radius=bend_radius_um, angle=-180)
    lower_right_arc = c << gf.path.extrude(lower_right_arc_path, width=waveguide_width_um, layer=layer)
    lower_right_arc.move((coupling_length_um / 2, -y_coupling))

    # ===== Lower tapers =====
    lower_taper_left = c << gf.components.taper(
        length=taper_length_um, width1=taper_tip_width_um, width2=waveguide_width_um, layer=layer)
    lower_taper_left.move((-coupling_length_um / 2 - arc_span - taper_length_um, -y_taper - waveguide_width_um / 2))

    lower_taper_right = c << gf.components.taper(
        length=taper_length_um, width1=waveguide_width_um, width2=taper_tip_width_um, layer=layer)
    lower_taper_right.move((coupling_length_um / 2 + arc_span, -y_taper - waveguide_width_um / 2))

    return c


if __name__ == "__main__":
    c = contra_dc_grating()
    c.write_gds("experiments/paper_swap/final5/output/recreation_opus45m/device.gds")
    print("Wrote device.gds")
