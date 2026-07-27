import gdsfactory as gf

@gf.cell
def symmetric_coupler_18x3():
    """
    Creates a symmetric directional coupler based on the provided image.
    Footprint constraint: 18um x 3um.
    """
    c = gf.Component()

    # 1. Define Dimensions
    # Total device footprint
    L = 18.0
    H_tot = 3.0
    
    # Revised parameters based on image analysis:
    # Comparison with Turn 4 output showed the previous waveguides (width=0.6) 
    # were too thin and the gap (0.3) too wide.
    # The target image has visually heavier waveguides and a tighter central gap.
    width = 0.8       # Increased width
    gap_min = 0.2     # Decreased gap at the waist
    
    # Derived parameters
    L_arm = L / 2.0   # Length of one half (Input to Waist)
    
    # Y-coordinates for the waveguide centers
    # At the inputs (ends), waveguides align to the outer boundary of the 3um box
    # Top WG top edge = 1.5 -> Center = 1.5 - width/2
    y_in_top = (H_tot / 2.0) - (width / 2.0)  # 1.1 um
    
    # At the waist (center), waveguides are separated by gap_min
    # Top WG bottom edge = gap_min/2 -> Center = gap_min/2 + width/2
    y_waist_top = (gap_min / 2.0) + (width / 2.0)  # 0.5 um
    
    # The vertical displacement (dy) for the top arm
    dy = y_in_top - y_waist_top  # 0.6 um

    # 2. Define Cross Section
    xs = gf.cross_section.cross_section(width=width, layer=(1, 0))

    # 3. Create S-bend Primitives
    # We use bend_s for a smooth adiabatic cosine/sine profile.
    
    # Bend for dropping down (Top-Left and Bottom-Right)
    # y changes by -dy
    bend_down = gf.components.bend_s(size=(L_arm, -dy), cross_section=xs)
    
    # Bend for rising up (Top-Right and Bottom-Left)
    # y changes by +dy
    bend_up = gf.components.bend_s(size=(L_arm, dy), cross_section=xs)

    # 4. Assembly - Top Arm
    # Top Left: Starts at input, curves down to waist
    tl = c << bend_down
    tl.move(origin=tl.ports["o1"].center, destination=(0, y_in_top))
    
    # Top Right: Starts at waist, curves up to output
    tr = c << bend_up
    tr.connect("o1", tl.ports["o2"])

    # 5. Assembly - Bottom Arm
    # Bottom Left: Starts at input (-y_in), curves UP to waist (-y_waist)
    bl = c << bend_up
    bl.move(origin=bl.ports["o1"].center, destination=(0, -y_in_top))
    
    # Bottom Right: Starts at waist (-y_waist), curves DOWN to output (-y_in)
    br = c << bend_down
    br.connect("o1", bl.ports["o2"])

    # 6. Add Ports
    c.add_port("o1", port=tl.ports["o1"]) # Top Input
    c.add_port("o2", port=bl.ports["o1"]) # Bottom Input
    c.add_port("o3", port=tr.ports["o2"]) # Top Output
    c.add_port("o4", port=br.ports["o2"]) # Bottom Output

    return c

# Create and save the device
if __name__ == "__main__":
    device = symmetric_coupler_18x3()
    device.write_gds("symmetric_coupler.gds")
    device.show()