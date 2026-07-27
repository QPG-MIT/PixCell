import gdsfactory as gf
from gdsfactory.components import straight, bend_circular, taper, rectangle
from gdsfactory.cross_section import cross_section

# 1. FIX: Define a custom cross_section with a small radius constraint.
# This overrides the default 10um limit that caused the ValueError.
xs = cross_section(width=0.2, layer=(1, 0), radius=0.1)

@gf.cell
def create_arm():
    """Creates a U-shaped arm with tapered ends."""
    c = gf.Component()
    
    # Define primitives using the custom cross-section
    t_in = c << taper(length=2, width1=0.1, width2=0.2, cross_section=xs)
    t_out = c << taper(length=2, width1=0.2, width2=0.1, cross_section=xs)
    
    # Use a small radius for the bend to match the visual footprint
    bend = c << bend_circular(radius=0.5, angle=180, cross_section=xs)
    
    # Straight sections
    s1 = c << straight(length=6, cross_section=xs)
    s2 = c << straight(length=6, cross_section=xs)
    
    # Connect geometry
    # Taper -> Straight -> Bend(180) -> Straight -> Taper
    s1.connect("o1", t_in.ports["o2"])
    bend.connect("o1", s1.ports["o2"])
    s2.connect("o1", bend.ports["o2"])
    t_out.connect("o1", s2.ports["o2"])
    
    # Expose ports
    c.add_port("o1", port=t_in.ports["o1"])
    c.add_port("o2", port=t_out.ports["o1"])
    
    return c

@gf.cell
def create_central_segmented_wg(length=18.24):
    """Creates the central waveguide with periodic stripes."""
    c = gf.Component()
    
    # Base waveguide
    base = c << straight(length=length, cross_section=xs)
    
    # Add stripes using rectangles
    num_stripes = 44
    stripe_width = 0.1
    spacing = length / num_stripes
    
    for i in range(num_stripes):
        # Using a secondary layer (1, 1) for the stripes to create contrast
        stripe = c << rectangle(size=(0.1, 0.4), layer=(1, 1), centered=True)
        stripe.move((i * spacing - length/2 + spacing/2, 0))
        
    return c

@gf.cell
def full_device():
    c = gf.Component()
    
    # 1. Add Central Section
    center = c << create_central_segmented_wg()
    
    # 2. Add Top Arm
    top = c << create_arm()
    top.move((0, 0.5)) # Offset vertically to clear central waveguide
    
    # 3. Add Bottom Arm (Mirrored and shifted)
    bottom = c << create_arm()
    bottom.mirror()
    bottom.move((0, -0.5))
    
    return c

# Generate the device
device = full_device()
device.write_gds("device.gds")
# device.show() # Uncomment to view in KLayout