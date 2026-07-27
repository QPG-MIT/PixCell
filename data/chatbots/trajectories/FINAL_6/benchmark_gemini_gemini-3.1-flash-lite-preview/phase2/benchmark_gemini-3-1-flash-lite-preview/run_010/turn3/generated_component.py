import gdsfactory as gf

@gf.cell
def petal_arm():
    """
    Creates a single arm unit.
    The ellipse is shifted to overlap at the center, forming a robust cross.
    """
    c = gf.Component()
    
    # 1. Create a thinner, more elongated elliptical lobe.
    # Using (1.0, 0.4) makes it more slender than the previous version.
    # By moving it to x=0.8, the left edge of the ellipse is at -0.2.
    # This ensures that when rotated 4 times, they overlap at the center 
    # to form a solid, rounded square junction.
    petal = c << gf.components.ellipse(radii=(1.0, 0.4), layer=(1, 0))
    petal.movex(0.8)
    
    # 2. Create the rectangular tip.
    # The ellipse ends at x = 0.8 + 1.0 = 1.8.
    # Placing the center of the rectangle (0.3 long) at 1.95 puts its 
    # start at 1.8 and its end at 2.1.
    tab = c << gf.components.rectangle(size=(0.3, 0.2), layer=(1, 0), centered=True)
    tab.movex(1.95)
    
    return c

@gf.cell
def cross_device():
    """
    Assembles 4 petal arms into a cross pattern.
    """
    c = gf.Component()
    
    # Add 4 instances, rotated to form the cross
    for angle in [0, 90, 180, 270]:
        arm = c << petal_arm()
        arm.rotate(angle)
        
    return c

# Create and write the device
device = cross_device()
device.write_gds("cross_device.gds")

# Footprint Analysis:
# The tip reaches 2.1um from the center.
# Total width = 2.1 * 2 = 4.2um, which is safely within the 4.7um constraint.