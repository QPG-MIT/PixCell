import gdsfactory as gf

# 1. Define a helper to create a positioned rectangle component
@gf.cell
def placed_rect(size, pos=(0, 0)):
    """Creates a component containing a rectangle at a specific position."""
    c = gf.Component()
    # Add rectangle as a reference (not directly as a polygon)
    ref = c << gf.components.rectangle(size=size, centered=True, layer=(1, 0))
    # Move the reference, not the component definition
    ref.move(pos)
    return c

@gf.cell
def comb_device():
    """
    Creates the comb structure by merging positioned rectangle components.
    """
    # 1. Define dimensions
    total_w = 25
    body_h = 4
    finger_w = 3
    finger_h = 3
    
    # 2. Create the main body component
    main_body = placed_rect(size=(total_w, body_h), pos=(0, 0))
    
    # 3. Create top fingers (4 count)
    top_positions = [-9, -3, 3, 9]
    top_fingers = [
        placed_rect(size=(finger_w, finger_h), pos=(x, (body_h / 2) + (finger_h / 2))) 
        for x in top_positions
    ]
    
    # 4. Create the bottom finger (1 count)
    bottom_finger = placed_rect(size=(finger_w, finger_h), pos=(0, -(body_h / 2) - (finger_h / 2)))
    
    # 5. Combine everything using boolean OR operations
    # Note: gf.boolean returns a new component containing the union of the shapes
    combined_structure = main_body
    
    for finger in top_fingers:
        combined_structure = gf.boolean(
            combined_structure, finger, operation="or", layer=(1, 0)
        )
        
    combined_structure = gf.boolean(
        combined_structure, bottom_finger, operation="or", layer=(1, 0)
    )
    
    return combined_structure

# Create and save the component
if __name__ == "__main__":
    c = comb_device()
    c.write_gds("comb_device.gds")
    c.show()