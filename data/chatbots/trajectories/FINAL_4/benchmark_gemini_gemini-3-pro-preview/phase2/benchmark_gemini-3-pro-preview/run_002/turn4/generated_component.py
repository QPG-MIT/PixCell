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
    # The waveguides in the target are thinner relative to the input gap than in the previous iteration.
    # Estimated ratio of Gap_in / Width is ~3.0. With H=3.0, this implies width ~0.6um.
    width = 0.6       
    
    # The target shows a small but clearly distinct gap at the waist.
    # Visually estimated at roughly half the waveguide width.
    gap_min = 0.3     
    
    # Derived parameters
    L_arm = L / 2.0   # Length of one half (S-bend length)
    
    # Y-coordinates for the waveguide centers
    # At the inputs (ends), waveguides align to the outer boundary of the 3um box
    # Top WG top edge = 1.5 -> Center = 1.5 - width/2
    y_in_top = (H_tot / 2.0) - (width / 2.0)
    
    # At the waist (center), waveguides are separated by gap_min
    # Top WG bottom edge = gap_min/2 -> Center = gap_min/2 + width/2
    y_waist_top = (gap_min / 2.0) + (width / 2.0)
    
    # The vertical displacement (dy) for the top arm
    dy = y_in_top - y_waist_top

    # 2. Define Cross Section
    xs = gf.cross_section.cross_section(width=width, layer=(1, 0))

    # 3. Create S-bend Primitives
    # bend_s creates a generic S-bend defined by size=(length, height_delta)
    # This generates the smooth adiabatic-like curvature.
    
    # Bend for Top-Left (High -> Low)
    # To drop by dy, height_delta should be -dy
    bend_down = gf.components.bend_s(size=(L_arm, -dy), cross_section=xs)
    
    # Bend for Top-Right (Low -> High)
    bend_up = gf.components.bend_s(size=(L_arm, dy), cross_section=xs)

    # 4. Assembly - Top Arm
    # Top Left: Starts left boundary, curves down to center waist
    # We position the end port (o2) at the waist coordinates (x=0, y=y_waist_top)
    tl = c << bend_down
    tl.move(origin=tl.ports["o2"].center, destination=(0, y_waist_top))
    
    # Top Right: Starts at center waist, curves up to right boundary
    tr = c << bend_up
    tr.connect("o1", tl.ports["o2"])

    # 5. Assembly - Bottom Arm
    # Bottom Left: Starts left boundary, curves up to center waist
    # y_waist_bot is -y_waist_top
    bl = c << bend_up
    bl.move(origin=bl.ports["o2"].center, destination=(0, -y_waist_top))
    
    # Bottom Right: Starts at center waist, curves down to right boundary
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