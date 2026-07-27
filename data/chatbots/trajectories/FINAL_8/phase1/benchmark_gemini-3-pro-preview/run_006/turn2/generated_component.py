import gdsfactory as gf
from gdsfactory.cross_section import Section

@gf.cell
def striped_coupler():
    """
    Corrected recreation using Multi-Section Cross Sections.
    This solves the 'pinching' artifact by extruding parallel lines along the path
    rather than simply copying the geometry.
    """
    c = gf.Component()

    # --- 1. Dimensions & Constraints ---
    # Footprint: 120um x 4um
    total_length = 120.0
    straight_length = 40.0
    bend_length = (total_length - straight_length) / 2  # 40.0

    # Stripe Parameters (Tuned for the visual "bold" look)
    # 5 stripes, roughly 50% duty cycle
    w = 0.15   # Line width
    g = 0.15   # Gap between lines
    pitch = w + g
    n_stripes = 5

    # --- 2. Define the Multi-Stripe Cross Section ---
    # We create a cross-section with 5 distinct sections.
    # We define offsets relative to the central path spine.
    # Offsets: -2p, -1p, 0, 1p, 2p
    
    sections = [
        Section(width=w, offset=1*pitch, layer=(1, 0)),
        Section(width=w, offset=2*pitch, layer=(1, 0)),
        Section(width=w, offset=-1*pitch, layer=(1, 0)),
        Section(width=w, offset=-2*pitch, layer=(1, 0)),
    ]
    
    # The main cross_section defines the center line (offset=0)
    # We attach the other 4 lines as 'sections'
    striped_xs = gf.cross_section.cross_section(
        width=w, 
        layer=(1, 0),
        sections=sections
    )

    # --- 3. Calculate Vertical Positions ---
    # We need to fit everything within 4um height.
    # Bundle Height = (4 * 0.3) + 0.15 = 1.35 um
    
    # Center Region:
    # We want a gap of ~0.15um between the Top Bundle and Bottom Bundle.
    # Top Bundle Center Y = (Bundle_Height/2) + (Gap/2)
    # y_c = (1.35 / 2) + (0.15 / 2) = 0.675 + 0.075 = 0.75
    y_center_mag = 0.75

    # Input/Output Region:
    # Separate them further. Max height is +/- 2.0.
    # Bundle extends 0.675 from its center.
    # Max Center Y = 2.0 - 0.675 = 1.325.
    # Let's use 1.3 to be safe.
    y_input_mag = 1.3

    # Vertical shift required for the S-bend
    # Top arm goes from 1.3 down to 0.75. dy = -0.55
    dy = y_center_mag - y_input_mag

    # --- 4. Build the Arms ---

    # -- Top Arm --
    top_arm = gf.Component("top_arm")
    
    # Input S-Bend (Down)
    b1 = top_arm << gf.components.bend_s(
        size=(bend_length, dy), 
        cross_section=striped_xs
    )
    
    # Center Straight
    st = top_arm << gf.components.straight(
        length=straight_length,
        cross_section=striped_xs
    )
    
    # Output S-Bend (Up)
    # Note: dy is negative, so -dy is positive (going back up)
    b2 = top_arm << gf.components.bend_s(
        size=(bend_length, -dy),
        cross_section=striped_xs
    )
    
    # Connect
    st.connect("o1", b1.ports["o2"])
    b2.connect("o1", st.ports["o2"])
    
    top_arm.add_port("o1", port=b1.ports["o1"])
    top_arm.add_port("o2", port=b2.ports["o2"])

    # -- Bottom Arm --
    bot_arm = gf.Component("bot_arm")
    
    # Bottom moves UP towards center, then DOWN.
    # Input y is negative (-1.3). Center y is negative (-0.75).
    # dy_bot = -0.75 - (-1.3) = +0.55. (This is exactly -dy)
    dy_bot = -dy
    
    # Input S-Bend (Up)
    b1_bot = bot_arm << gf.components.bend_s(
        size=(bend_length, dy_bot), 
        cross_section=striped_xs
    )
    
    # Center Straight
    st_bot = bot_arm << gf.components.straight(
        length=straight_length,
        cross_section=striped_xs
    )
    
    # Output S-Bend (Down)
    b2_bot = bot_arm << gf.components.bend_s(
        size=(bend_length, -dy_bot),
        cross_section=striped_xs
    )
    
    st_bot.connect("o1", b1_bot.ports["o2"])
    b2_bot.connect("o1", st_bot.ports["o2"])
    
    bot_arm.add_port("o1", port=b1_bot.ports["o1"])
    bot_arm.add_port("o2", port=b2_bot.ports["o2"])

    # --- 5. Assembly ---
    # Add references to the main component
    ref_top = c << top_arm
    ref_bot = c << bot_arm

    # Move them to starting positions
    # Top starts at (-L/2, +1.3)
    # Bottom starts at (-L/2, -1.3)
    ref_top.move( (-total_length/2, y_input_mag) )
    ref_bot.move( (-total_length/2, -y_input_mag) )

    return c

if __name__ == "__main__":
    device = striped_coupler()
    device.show()
    device.write_gds("striped_coupler_fixed.gds")
    
    print(f"Device: {device.name}")
    print(f"BBox: {device.bbox}")