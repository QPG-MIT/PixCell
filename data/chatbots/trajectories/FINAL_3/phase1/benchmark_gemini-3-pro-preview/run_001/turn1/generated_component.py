import gdsfactory as gf

@gf.cell
def directional_coupler_4x240():
    """
    Creates a directional coupler based on visual analysis and footprint constraints.
    Footprint: 4 um x 240 um.
    """
    c = gf.Component()

    # 1. Define Parameters based on constraints
    total_length = 240.0
    total_height = 4.0
    wg_width = 0.5
    gap = 0.2
    
    # Partition length into 3 segments (Bend - Straight - Bend)
    # Visual analysis suggests segments are roughly equal length
    l_straight = 80.0
    l_bend = (total_length - l_straight) / 2  # Result: 80.0
    
    # Calculate vertical geometry (y-coordinates relative to center y=0)
    # Inner: Center of waveguides in the coupling region
    y_center_inner = (gap + wg_width) / 2
    
    # Outer: Center of waveguides at input/output ports
    # Top edge is at +2.0 (half of 4.0), so center is at 2.0 - wg_width/2
    y_center_outer = (total_height / 2) - (wg_width / 2)
    
    # The vertical displacement (dy) for the S-bends
    dy_bend = y_center_outer - y_center_inner

    # Define Cross Section
    # Using the standard cross_section reference from the catalog
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))

    # ---------------------------------------------------------
    # 2. Create Primitives
    # ---------------------------------------------------------
    
    # Central Coupling Region (Two straight waveguides)
    wg_top = c << gf.components.straight(length=l_straight, cross_section=xs)
    wg_bot = c << gf.components.straight(length=l_straight, cross_section=xs)

    # Position the central waveguides
    wg_top.y = y_center_inner
    wg_bot.y = -y_center_inner

    # Input S-Bends (Left side)
    # Top Left Bend: Needs to go DOWN from input to coupler
    # bend_s size is (length, height_change)
    bend_in_top = c << gf.components.bend_s(size=(l_bend, -dy_bend), cross_section=xs)
    
    # Bottom Left Bend: Needs to go UP from input to coupler
    bend_in_bot = c << gf.components.bend_s(size=(l_bend, dy_bend), cross_section=xs)

    # Output S-Bends (Right side)
    # Top Right Bend: Needs to go UP from coupler to output
    bend_out_top = c << gf.components.bend_s(size=(l_bend, dy_bend), cross_section=xs)
    
    # Bottom Right Bend: Needs to go DOWN from coupler to output
    bend_out_bot = c << gf.components.bend_s(size=(l_bend, -dy_bend), cross_section=xs)

    # ---------------------------------------------------------
    # 3. Assemble and Connect
    # ---------------------------------------------------------

    # Connect Left Side (Inputs -> Coupling Region)
    # Connect bend output ("o2") to straight input ("o1")
    bend_in_top.connect("o2", wg_top.ports["o1"])
    bend_in_bot.connect("o2", wg_bot.ports["o1"])

    # Connect Right Side (Coupling Region -> Outputs)
    # Connect bend input ("o1") to straight output ("o2")
    bend_out_top.connect("o1", wg_top.ports["o2"])
    bend_out_bot.connect("o1", wg_bot.ports["o2"])

    # ---------------------------------------------------------
    # 4. Expose Ports
    # ---------------------------------------------------------
    c.add_port("o1", port=bend_in_bot.ports["o1"]) # Input Bottom
    c.add_port("o2", port=bend_in_top.ports["o1"]) # Input Top
    c.add_port("o3", port=bend_out_top.ports["o2"]) # Output Top
    c.add_port("o4", port=bend_out_bot.ports["o2"]) # Output Bottom

    return c

if __name__ == "__main__":
    # Generate and Save
    device = directional_coupler_4x240()
    try:
        device.show() # View in KLayout/GDS viewer
    except Exception:
        pass # Gracefully handle if klive is not connected
    device.write_gds("directional_coupler_4x240.gds")