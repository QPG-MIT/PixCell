import gdsfactory as gf

# Tunable parameters (function-defining knobs)
wg_width = 0.50  # Base waveguide width in μm
wg_spacing = 0.65  # Center-to-center spacing in μm
left_section_length = 5.0  # Length of left straight section in μm
taper_length = 20.0  # Length of taper region in μm
taper_tip_width = 0.15  # Width at narrow end of taper in μm
center_wg_offset = 6.0  # Offset from left edge for center guide in μm
center_wg_length = 20.0  # Length of center waveguide in μm

@gf.cell
def coupler_3port():
    """
    3-port directional coupler with S-curve taper transitions.
    Top and bottom guides have tapered bends; center guide is shorter and offset.
    Total length = 40 μm.
    """
    c = gf.Component()

    # Y positions for the three guides (top, center, bottom)
    y_top = wg_spacing
    y_center = 0.0
    y_bottom = -wg_spacing

    # === TOP WAVEGUIDE ===
    # Left straight section
    top_left = gf.components.straight(length=left_section_length, width=wg_width)
    top_left_ref = c.add_ref(top_left)
    top_left_ref.move((0, y_top))

    # Taper section
    top_taper = gf.components.taper(
        length=taper_length,
        width1=wg_width,
        width2=taper_tip_width,
        layer=(1, 0)
    )
    top_taper_ref = c.add_ref(top_taper)
    top_taper_ref.move((left_section_length, y_top))

    # Right section
    right_length = 40.0 - left_section_length - taper_length
    top_right = gf.components.straight(length=right_length, width=taper_tip_width)
    top_right_ref = c.add_ref(top_right)
    top_right_ref.move((left_section_length + taper_length, y_top))

    # === CENTER WAVEGUIDE (shorter, offset) ===
    center = gf.components.straight(length=center_wg_length, width=wg_width)
    center_ref = c.add_ref(center)
    center_ref.move((center_wg_offset, y_center))

    # === BOTTOM WAVEGUIDE ===
    # Left straight section
    bottom_left = gf.components.straight(length=left_section_length, width=wg_width)
    bottom_left_ref = c.add_ref(bottom_left)
    bottom_left_ref.move((0, y_bottom))

    # Taper section
    bottom_taper = gf.components.taper(
        length=taper_length,
        width1=wg_width,
        width2=taper_tip_width,
        layer=(1, 0)
    )
    bottom_taper_ref = c.add_ref(bottom_taper)
    bottom_taper_ref.move((left_section_length, y_bottom))

    # Right section
    bottom_right = gf.components.straight(length=right_length, width=taper_tip_width)
    bottom_right_ref = c.add_ref(bottom_right)
    bottom_right_ref.move((left_section_length + taper_length, y_bottom))

    c.flatten()
    return c

if __name__ == "__main__":
    cell = coupler_3port()
    cell.write_gds("device.gds")
    print(f"Device written to device.gds")
