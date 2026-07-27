import gdsfactory as gf

@gf.cell
def coupler_half(length_tail=10.0, length_sbend=25.0, length_coupler=50.0, dy=1.3, width=0.6):
    """Creates the top half of the directional coupler."""
    c = gf.Component()
    xs = gf.cross_section.strip(width=width, layer=(1, 0))

    # Create segments
    tail_left = c << gf.components.straight(length=length_tail, cross_section=xs)
    sbend_in = c << gf.components.bend_s(size=(length_sbend, -dy), cross_section=xs)
    mid = c << gf.components.straight(length=length_coupler, cross_section=xs)
    sbend_out = c << gf.components.bend_s(size=(length_sbend, dy), cross_section=xs)
    tail_right = c << gf.components.straight(length=length_tail, cross_section=xs)

    # Chain them together
    sbend_in.connect("o1", tail_left.ports["o2"])
    mid.connect("o1", sbend_in.ports["o2"])
    sbend_out.connect("o1", mid.ports["o2"])
    tail_right.connect("o1", sbend_out.ports["o2"])

    # Add external ports for the half-branch
    c.add_port("o1", port=tail_left.ports["o1"])
    c.add_port("o2", port=tail_right.ports["o2"])
    return c

@gf.cell
def symmetric_directional_coupler():
    """
    Symmetric directional coupler with smooth adiabatic transitions.
    
    Target Footprint: 120um x 4um
    Width: 0.6um
    Gap: 0.2um
    """
    c = gf.Component("directional_coupler")
    
    # 1. Geometry Math
    # Total Width: 10 + 25 + 50 + 25 + 10 = 120um
    # To hit 4um height: outer centerline at 1.7 (1.7 + 0.3 = 2.0 edge)
    # For 0.2um gap: inner centerline at 0.4 (0.4 - 0.3 = 0.1 edge)
    # Required S-bend drop (dy) = 1.7 - 0.4 = 1.3um
    width = 0.6
    dy_val = 1.3
    
    # 2. Instantiate the branches
    half = coupler_half(dy=dy_val, width=width)
    
    top_branch = c << half
    bot_branch = c << half
    
    # 3. Position and Mirror
    # Place top branch so its inner coupling section is at y = +0.4
    # The 'half' component starts at y=0, drops by dy, then goes back up.
    # Its lowest point (coupling region) is at -dy.
    # To put that point at +0.4, we move it up by (0.4 + dy)
    top_branch.movey(0.4 + dy_val)
    
    # Mirror the bottom branch across the X-axis
    bot_branch.mirror_y()
    # Position bottom branch at y = -0.4 (symmetric to top)
    bot_branch.movey(-(0.4 + dy_val))
    
    # 4. Define Device Ports
    # Convention: o1, o2 on left (bottom, top) | o3, o4 on right (top, bottom)
    c.add_port("o1", port=bot_branch.ports["o1"])
    c.add_port("o2", port=top_branch.ports["o1"])
    c.add_port("o3", port=top_branch.ports["o2"])
    c.add_port("o4", port=bot_branch.ports["o2"])

    return c

if __name__ == "__main__":
    # Create the component
    dc = symmetric_directional_coupler()
    
    # Save GDS
    dc.write_gds("symmetric_directional_coupler_v4.gds")
    
    # Verify Footprint
    bbox = dc.dbbox()
    print(f"GDS saved: symmetric_directional_coupler_v4.gds")
    print(f"Footprint: {bbox.width():.2f} um x {bbox.height():.2f} um")
    
    # Display
    dc.show()