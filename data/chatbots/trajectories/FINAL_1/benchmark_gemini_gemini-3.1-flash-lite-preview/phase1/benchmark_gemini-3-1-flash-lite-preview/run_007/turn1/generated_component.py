import gdsfactory as gf

@gf.cell
def tapered_structure():
    """
    Constructs the tapered device geometry using parametric primitives 
    and boolean operations.
    """
    c = gf.Component()
    
    # Define design parameters based on the 40um x 1.7um footprint
    length = 40.0
    y_offset = 0.6  # Separation to achieve ~1.7um total height
    
    # 1. Create parametric primitives (tapers)
    # Center taper: Starts wide (0.7), ends narrow (0.2)
    center_taper = gf.components.taper(length=length, width1=0.7, width2=0.2)
    
    # Outer tapers: Start narrow (0.1), end wide (0.5)
    # We create one, then copy it for the bottom
    outer_taper = gf.components.taper(length=length, width1=0.1, width2=0.5)
    
    # 2. Position the primitives
    # Create references to perform movements
    ref_center = c << center_taper
    ref_top = c << outer_taper
    ref_bottom = c << outer_taper
    
    ref_top.movey(y_offset)
    ref_bottom.movey(-y_offset)
    
    # 3. Combine into a single geometry using Boolean operations
    # We combine the three referenced components into one final shape
    final_device = gf.boolean(ref_center, ref_top, operation="or", layer=(1, 0))
    final_device = gf.boolean(final_device, ref_bottom, operation="or", layer=(1, 0))
    
    # Add the result to the main component
    c.add_ref(final_device)
    
    return c

# Create and save the component
if __name__ == "__main__":
    device = tapered_structure()
    # device.show()  # Uncomment to visualize in KLayout
    device.write_gds("tapered_device.gds")