import gdsfactory as gf

@gf.cell
def custom_device():
    """
    Recreates the device geometry using tapered primitives for the fingers
    and boolean union to merge the components.
    """
    c = gf.Component()
    layer = (1, 0)
    
    # 1. Create the base block (25um wide x 10um tall)
    # Using a rectangle
    base = gf.components.rectangle(size=(25, 10), layer=layer, centered=True)
    
    # 2. Create the tapered fingers
    # Using 'taper'. Length=5, Base width=2.5, Tip width=1.0
    finger_template = gf.components.taper(length=5, width1=2.5, width2=1.0, layer=layer)
    
    # 3. Create the bottom tab
    # Using a small rectangle
    tab_template = gf.components.rectangle(size=(2, 2), layer=layer, centered=True)
    
    # Prepare the union: Start with the base
    final_shape = base
    
    # 4. Add the 4 Fingers
    # The taper is horizontal by default, so we rotate 90 degrees.
    # The center of the taper is its midpoint (length/2).
    # To place the bottom of the taper at the top of the base (y=5):
    # We move the center to y = 5 + (length/2) = 5 + 2.5 = 7.5
    finger_positions = [-9, -3, 3, 9]
    for x in finger_positions:
        f_comp = gf.Component()
        ref = f_comp << finger_template
        ref.rotate(90)
        ref.move((x, 7.5)) 
        
        # Boolean OR to add finger to shape
        final_shape = gf.boolean(final_shape, f_comp, operation="or", layer=layer)
        
    # 5. Add the Bottom Tab
    # Move to bottom center: (0, -6)
    t_comp = gf.Component()
    ref_t = t_comp << tab_template
    ref_t.move((0, -6)) 
    
    # Boolean OR to add tab to shape
    final_shape = gf.boolean(final_shape, t_comp, operation="or", layer=layer)
    
    # Add final unioned geometry to main component
    c << final_shape
    
    return c

# Generate and save the device
if __name__ == "__main__":
    device = custom_device()
    device.write_gds("device.gds")
    print("GDS file 'device.gds' produced successfully with tapered fingers.")