import gdsfactory as gf

@gf.cell
def petal_arm():
    """
    Creates a single arm unit.
    The petal is offset from the origin so that when rotated, 
    it overlaps at (0,0) to create a solid center.
    """
    c = gf.Component()
    
    # 1. Create the elliptical lobe
    # Radii (1.0, 0.5) creates a shape extending 1.0um from center.
    # We move it by x=1.0 so the base touches the origin (0,0).
    petal = c << gf.components.ellipse(radii=(1.0, 0.5), layer=(1, 0))
    petal.movex(1.0)
    
    # 2. Create the rectangular tip
    # Place it at the end of the ellipse.
    # x=2.0 is the end of the ellipse, so we place the rect at 2.1
    tab = c << gf.components.rectangle(size=(0.4, 0.25), layer=(1, 0), centered=True)
    tab.movex(2.1)
    
    return c

@gf.cell
def cross_device():
    """
    Assembles 4 petal arms. 
    Because they start at (0,0), they will overlap at the center 
    to form the fused cross shape.
    """
    c = gf.Component()
    
    # Add 4 instances, rotated
    for angle in [0, 90, 180, 270]:
        arm = c << petal_arm()
        arm.rotate(angle)
        
    return c

# Create and write the device
device = cross_device()
device.write_gds("cross_device.gds")

# Total footprint analysis:
# The tip reaches 2.1 + 0.2 = 2.3um from the center.
# Total width = 2.3 * 2 = 4.6um, which fits within the 4.7um constraint.