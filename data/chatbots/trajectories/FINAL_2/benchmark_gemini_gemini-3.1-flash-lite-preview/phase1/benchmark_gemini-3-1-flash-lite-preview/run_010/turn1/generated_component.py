import gdsfactory as gf

@gf.cell
def custom_device():
    """
    Constructs the device geometry using parametric primitives
    and combines them using boolean operations.
    """
    c = gf.Component()
    layer = (1, 0)
    
    # 1. Create the base block (25um wide x 6um tall)
    base = gf.components.rectangle(size=(25, 6), layer=layer, centered=True)
    
    # 2. Define templates for fingers and tab
    # Fingers: 2um x 2um squares
    finger_template = gf.components.rectangle(size=(2, 2), layer=layer, centered=True)
    # Tab: 2um x 1um rectangle
    tab_template = gf.components.rectangle(size=(2, 1), layer=layer, centered=True)
    
    # Start the boolean union with the base
    final_shape = base
    
    # 3. Add 4 Fingers (positioned on top edge of base)
    # Positions spaced across the top
    finger_positions = [-9, -3, 3, 9]
    for x in finger_positions:
        # Create a component for the finger and move it
        f_comp = gf.Component()
        ref = f_comp << finger_template
        ref.move((x, 4.0)) # Y-offset: Base height 6/2 + finger height 2/2 = 4
        
        # Boolean OR to add finger to shape
        final_shape = gf.boolean(final_shape, f_comp, operation="or", layer=layer)
        
    # 4. Add the Bottom Tab
    t_comp = gf.Component()
    ref_t = t_comp << tab_template
    ref_t.move((0, -3.5)) # Y-offset: -3 (base bottom) - 0.5 (half tab height)
    
    # Boolean OR to add tab to shape
    final_shape = gf.boolean(final_shape, t_comp, operation="or", layer=layer)
    
    # Add final unioned geometry to main component
    c << final_shape
    
    return c

# Generate and save the device
if __name__ == "__main__":
    device = custom_device()
    # Explicitly write the file
    device.write_gds("device.gds")
    print("GDS file 'device.gds' produced successfully.")