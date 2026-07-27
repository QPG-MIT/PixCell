import gdsfactory as gf

@gf.cell
def adiabatic_coupler():
    c = gf.Component()
    
    # 1. Define Dimensions based on Footprint Constraint [18, 3]
    total_length = 18.0
    total_height = 3.0
    
    # Visual estimates for width and gap
    wg_width = 0.6
    min_gap = 0.4
    
    # 2. Calculate coordinates
    # Divide length into two halves for the symmetric structure
    half_length = total_length / 2.0
    
    # Determine Y-positions for the top waveguide
    # At the ends (x=0, x=18), the waveguide is at the outer edge of the 3um height.
    # Top edge = 1.5, so Center = 1.5 - (width/2)
    y_top_end = (total_height / 2.0) - (wg_width / 2.0)
    
    # At the center (x=9), the waveguide is close to the middle.
    # Center Y = (gap/2) + (width/2)
    y_top_center = (min_gap / 2.0) + (wg_width / 2.0)
    
    # Calculate the vertical displacement (dy) required for the S-bend
    # For top-left: goes from High (End) to Low (Center)
    dy = y_top_center - y_top_end  # This will be negative

    # 3. Define Cross-section
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))

    # 4. Build Top Waveguide Path (Left: Down, Right: Up)
    # bend_s creates a smooth cosine/sine curve from (0,0) to size=(x,y)
    tl = c << gf.components.bend_s(size=(half_length, dy), cross_section=xs)
    tr = c << gf.components.bend_s(size=(half_length, -dy), cross_section=xs)
    
    # Position Top Left start point
    tl.move((0, y_top_end))
    
    # Connect Top Right to Top Left
    tr.connect("o1", tl.ports["o2"])

    # 5. Build Bottom Waveguide Path (Left: Up, Right: Down)
    # Symmetric to top, but dy is inverted relative to the start position
    # Bottom Start Y is negative of Top Start Y
    y_bot_end = -y_top_end
    
    # Bottom Left must go UP (positive displacement of magnitude |dy|)
    bl = c << gf.components.bend_s(size=(half_length, -dy), cross_section=xs)
    br = c << gf.components.bend_s(size=(half_length, dy), cross_section=xs)
    
    # Position Bottom Left start point
    bl.move((0, y_bot_end))
    
    # Connect Bottom Right to Bottom Left
    br.connect("o1", bl.ports["o2"])

    # 6. Add Ports (Optional, preserves connectivity for larger circuits)
    c.add_port("o1", port=tl.ports["o1"])
    c.add_port("o2", port=bl.ports["o1"])
    c.add_port("o3", port=tr.ports["o2"])
    c.add_port("o4", port=br.ports["o2"])

    return c

# Create and save the geometry
device = adiabatic_coupler()
device.write_gds("adiabatic_coupler.gds")