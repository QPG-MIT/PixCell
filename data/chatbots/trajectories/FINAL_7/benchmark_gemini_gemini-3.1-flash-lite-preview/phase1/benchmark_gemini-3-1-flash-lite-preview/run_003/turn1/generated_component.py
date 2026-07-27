import gdsfactory as gf

@gf.cell
def racetrack_device():
    """
    Recreates the device geometry:
    A racetrack loop with two internal rectangular blocks.
    Footprint: [3.0, 5.5]
    """
    c = gf.Component()
    
    # Define a custom cross_section to allow small bend radii 
    # compatible with the [3.0, 5.5] footprint.
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0), radius=1.0)
    
    # 1. Define geometry parameters
    # The footprint is 3.0 x 5.5.
    # Radius = 1.0 (Diameter = 2.0).
    # Vertical straight length = Total Height - 2*Radius = 5.5 - 2.0 = 3.5.
    radius = 1.0
    vertical_straight_len = 1.75 # Length per side (total 3.5)
    
    # 2. Create primitives
    # 4 bends for the corners
    tl = c << gf.components.bend_circular(radius=radius, angle=90, cross_section=xs)
    tr = c << gf.components.bend_circular(radius=radius, angle=90, cross_section=xs)
    bl = c << gf.components.bend_circular(radius=radius, angle=90, cross_section=xs)
    br = c << gf.components.bend_circular(radius=radius, angle=90, cross_section=xs)
    
    # 2 vertical straight segments
    left_wg = c << gf.components.straight(length=vertical_straight_len, cross_section=xs)
    right_wg = c << gf.components.straight(length=vertical_straight_len, cross_section=xs)
    
    # 3. Assemble the loop
    # Connect left side
    tl.connect("o1", left_wg.ports["o1"])
    bl.connect("o2", left_wg.ports["o2"])
    
    # Connect right side
    tr.connect("o2", right_wg.ports["o2"])
    br.connect("o1", right_wg.ports["o1"])
    
    # Close top and bottom to form the racetrack
    tl.connect("o2", tr.ports["o1"])
    bl.connect("o1", br.ports["o2"])
    
    # 4. Add internal rectangular blocks
    # Centered inside the racetrack
    rect = gf.components.rectangle(size=(0.4, 1.5), layer=(1, 0), centered=True)
    
    # Position rectangles with a small gap between them
    b1 = c << rect
    b1.move((-0.3, 0)) 
    
    b2 = c << rect
    b2.move((0.3, 0))
    
    return c

# Generate the GDS file
device = racetrack_device()
device.write_gds("racetrack_device.gds")