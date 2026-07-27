import gdsfactory as gf

@gf.cell
def four_lobe_cross():
    """
    Creates a four-lobed cross pattern with elongated elliptical arms.
    Matches the footprint of 4.7 x 4.7 microns.
    """
    c = gf.Component()
    
    # Dimensions based on 4.7 x 4.7 um footprint
    total_length = 4.7   # Full span in each direction
    arm_thickness = 0.65  # Thickness of each arm (narrower for more elongation)
    
    # Create horizontal ellipse (very wide and flat)
    # This creates the left and right lobes
    h_ellipse = gf.components.ellipse(
        radii=(total_length/2, arm_thickness),
        layer=(1, 0)
    )
    
    # Create vertical ellipse (very tall and narrow)
    # This creates the top and bottom lobes
    v_ellipse = gf.components.ellipse(
        radii=(arm_thickness, total_length/2),
        layer=(1, 0)
    )
    
    # Combine using boolean OR to create the four-lobed cross
    result = gf.boolean(h_ellipse, v_ellipse, operation="or", layer=(1, 0))
    
    # Add the result to the component
    c << result
    
    return c

# Create and save the device
device = four_lobe_cross()
device.write_gds("four_lobe_cross.gds")
print(f"Device created with bounding box: {device.bbox}")