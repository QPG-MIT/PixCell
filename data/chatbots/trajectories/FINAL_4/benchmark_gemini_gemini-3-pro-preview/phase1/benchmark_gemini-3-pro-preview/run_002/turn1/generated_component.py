import gdsfactory as gf

@gf.cell
def symmetric_coupler_18x3():
    """
    Creates a symmetric directional coupler based on the provided image.
    Footprint constraint: 18um x 3um.
    """
    c = gf.Component()

    # 1. Define Dimensions
    # Total device size
    L = 18.0
    H_tot = 3.0
    
    # Waveguide parameters
    width = 0.5       # Standard waveguide width
    gap_min = 0.2     # Minimum gap at the center waist
    
    # Derived parameters
    L_arm = L / 2.0   # Length of one half (S-bend length)
    
    # Y-coordinates for the waveguide centers
    # At the inputs (ends), the waveguides are at the outer limits
    # y_in = (Height/2) - (Width/2)
    y_in = (H_tot - width) / 2.0  # 1.25
    
    # At the waist (center), the waveguides are separated by gap_min
    # y_waist = (Gap/2) + (Width/2)
    y_waist = (gap_min + width) / 2.0 # 0.35
    
    # The vertical displacement (dy) for the S-bends
    dy = y_in - y_waist # 0.9

    # 2. Define Cross Section
    xs = gf.cross_section.cross_section(width=width, layer=(1, 0))

    # 3. Create S-bend Primitives
    # Bend going down (dy < 0): Input High -> Output Low
    bend_down = gf.components.bend_s(size=(L_arm, -dy), cross_section=xs)
    
    # Bend going up (dy > 0): Input Low -> Output High
    bend_up = gf.components.bend_s(size=(L_arm, dy), cross_section=xs)

    # 4. Assembly - Top Arm
    # Top Left (Input -> Waist): Flows Left-to-Right, High-to-Low
    tl = c << bend_down
    # FIX: Use .center to pass coordinate tuple instead of Port object
    tl.move(origin=tl.ports["o2"].center, destination=(0, y_waist))
    
    # Top Right (Waist -> Output): Flows Left-to-Right, Low-to-High
    tr = c << bend_up
    # Connect start ('o1') to the end of the previous section
    tr.connect("o1", tl.ports["o2"])

    # 5. Assembly - Bottom Arm
    # Bottom Left (Input -> Waist): Flows Left-to-Right, Low-to-High (approaching center)
    bl = c << bend_up
    # FIX: Use .center to pass coordinate tuple instead of Port object
    bl.move(origin=bl.ports["o2"].center, destination=(0, -y_waist))
    
    # Bottom Right (Waist -> Output): Flows Left-to-Right, High-to-Low (diverging)
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