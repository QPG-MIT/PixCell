import gdsfactory as gf

@gf.cell
def single_petal():
    """
    Creates a single tapered petal arm.
    """
    c = gf.Component()
    
    # 1. Define the path of the petal
    # The petal extends 1.4um from the center.
    p = gf.path.straight(length=1.4)
    
    # 2. Define the cross-section transition
    # Base is 1.4um wide (so the four arms form a nice central junction)
    # Tip is 0.3um wide (matching the target taper)
    xs1 = gf.cross_section.cross_section(width=1.4, layer=(1, 0))
    xs2 = gf.cross_section.cross_section(width=0.3, layer=(1, 0))
    
    # Using 'sine' width_type for a smooth, natural taper
    transition = gf.path.transition(xs1, xs2, width_type='sine')
    
    # 3. Extrude the path into the petal component
    # This creates the tapered shape
    petal = c << gf.path.extrude_transition(p, transition)
    
    # 4. Add the rectangular tip at the end of the petal
    # The transition ends at 1.4um. The rectangle is 0.4um long.
    # We place its center at 1.4 + 0.2 = 1.6um to seamlessly extend the petal.
    tip = c << gf.components.rectangle(size=(0.4, 0.3), layer=(1, 0), centered=True)
    tip.movex(1.4 + 0.2)
    
    return c

@gf.cell
def cross_device():
    """
    Assembles 4 tapered petal arms into a symmetric cross.
    """
    c = gf.Component()
    
    # Add 4 instances, rotated to form the cross
    for angle in [0, 90, 180, 270]:
        arm = c << single_petal()
        arm.rotate(angle)
        
    return c

# Create and write the device
device = cross_device()
device.write_gds("cross_device.gds")

# Footprint Analysis:
# The arm length is 1.4um + 0.2um (tip half-length) = 1.6um.
# Total diameter = 1.6 * 2 = 3.2um.
# 3.2um is well within the 4.7um constraint.