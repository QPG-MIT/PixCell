import gdsfactory as gf

@gf.cell
def four_lobe_cross():
    """
    Creates a four-lobed cross pattern with elliptical arms.
    Matches the footprint of 4.7 x 4.7 microns.
    """
    c = gf.Component()
    
    # Dimensions based on 4.7 x 4.7 um footprint
    total_length = 4.7   # Full span in each direction
    lobe_width = 1.6     # Width of each arm
    
    # Create horizontal ellipse (stretched in x-direction)
    h_ellipse = gf.components.ellipse(
        radii=(total_length/2, lobe_width/2),
        layer=(1, 0)
    )
    
    # Create vertical ellipse (stretched in y-direction)
    v_ellipse = gf.components.ellipse(
        radii=(lobe_width/2, total_length/2),
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