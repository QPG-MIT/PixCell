"""
Contra-directional coupler with grating-assisted coupling
Parametric recreation from device_bw.png
TOPOLOGY: Two horizontal tapered waveguides with central grating region (18.24 x 0.7 um)
"""
import gdsfactory as gf

# Function-defining tunables (top-level contract)
waveguide_width = 0.32  # um - waveguide width in grating section
waveguide_gap = 0.08  # um - vertical gap between waveguides
grating_period = 0.32  # um - Bragg grating period
duty_cycle = 0.5  # fraction - grating tooth fill ratio
num_periods = 38  # integer - number of grating periods
grating_length = 12.16  # um - length of grating section (num_periods * period)
taper_length = 3.04  # um - taper on each end
taper_tip_width = 0.06  # um - narrow end width

# Layer
layer = (1, 0)


@gf.cell
def contra_directional_coupler() -> gf.Component:
    """
    Two parallel horizontal tapered waveguides with gratings.
    Target footprint: 18.24 um x 0.7 um
    """
    c = gf.Component()

    # Vertical centerlines
    y_top = (waveguide_gap + waveguide_width) / 2
    y_bottom = -(waveguide_gap + waveguide_width) / 2

    # TOP WAVEGUIDE
    # Left taper
    taper_top_left = gf.components.taper(
        length=taper_length,
        width1=taper_tip_width,
        width2=waveguide_width,
        layer=layer
    )
    tl = c << taper_top_left
    tl.xmin = 0
    tl.y = y_top

    # Central straight section
    straight_top = gf.components.rectangle(
        size=(grating_length, waveguide_width),
        layer=layer
    )
    st = c << straight_top
    st.xmin = taper_length
    st.y = y_top

    # Right taper
    taper_top_right = gf.components.taper(
        length=taper_length,
        width1=waveguide_width,
        width2=taper_tip_width,
        layer=layer
    )
    tr = c << taper_top_right
    tr.xmin = taper_length + grating_length
    tr.y = y_top

    # BOTTOM WAVEGUIDE
    # Left taper
    taper_bottom_left = gf.components.taper(
        length=taper_length,
        width1=taper_tip_width,
        width2=waveguide_width,
        layer=layer
    )
    bl = c << taper_bottom_left
    bl.xmin = 0
    bl.y = y_bottom

    # Central straight section
    straight_bottom = gf.components.rectangle(
        size=(grating_length, waveguide_width),
        layer=layer
    )
    sb = c << straight_bottom
    sb.xmin = taper_length
    sb.y = y_bottom

    # Right taper
    taper_bottom_right = gf.components.taper(
        length=taper_length,
        width1=waveguide_width,
        width2=taper_tip_width,
        layer=layer
    )
    br = c << taper_bottom_right
    br.xmin = taper_length + grating_length
    br.y = y_bottom

    # ADD GRATINGS (teeth on facing edges)
    tooth_width = grating_period * duty_cycle
    tooth_height = waveguide_width * 0.32

    x_grating_start = taper_length

    for i in range(num_periods):
        tooth_x = x_grating_start + i * grating_period

        # Top waveguide tooth (extends downward)
        tooth_t = c << gf.components.rectangle(
            size=(tooth_width, tooth_height),
            layer=layer
        )
        tooth_t.xmin = tooth_x
        tooth_t.ymax = y_top - waveguide_width / 2

        # Bottom waveguide tooth (extends upward)
        tooth_b = c << gf.components.rectangle(
            size=(tooth_width, tooth_height),
            layer=layer
        )
        tooth_b.xmin = tooth_x
        tooth_b.ymin = y_bottom + waveguide_width / 2

    return c


if __name__ == "__main__":
    component = contra_directional_coupler()
    component.write_gds("device.gds")
    print(f"Generated device.gds")
