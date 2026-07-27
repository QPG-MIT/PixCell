import gdsfactory as gf

@gf.cell
def comb_device():
    """
    Creates the comb structure by merging positioned rectangles 
    into a single boolean union.
    """
    layer = (1, 0)
    
    # Dimensions derived from the 25x10 footprint
    body_size = (25, 4)
    finger_size = (3, 3)
    
    # 1. Helper function to create a component with a rectangle at a specific position
    # This prevents the "cannot be modified" error by creating a container for the reference
    def get_part(size, pos):
        c = gf.Component()
        ref = c << gf.components.rectangle(size=size, layer=layer, centered=True)
        ref.move(pos)
        return c

    # 2. Build the list of components (Body + 4 Top Fingers + 1 Bottom Finger)
    parts = []
    
    # Add the main body
    parts.append(get_part(body_size, (0, 0)))
    
    # Add 4 Top Fingers (Positions: -9, -3, 3, 9)
    # Calculation: body height is 4, so top edge is at y=2. 
    # Finger height is 3, so its center is 2 + (3/2) = 3.5
    for x in [-9, -3, 3, 9]:
        parts.append(get_part(finger_size, (x, 3.5)))
        
    # Add 1 Bottom Finger
    # Calculation: bottom edge is at y=-2. 
    # Finger height is 3, so its center is -2 - (3/2) = -3.5
    parts.append(get_part(finger_size, (0, -3.5)))
    
    # 3. Combine everything into a single union
    # We use a running total to boolean-OR all parts together
    combined = parts[0]
    for i in range(1, len(parts)):
        combined = gf.boolean(
            combined, 
            parts[i], 
            operation="or", 
            layer=layer
        )
        
    return combined

# Create and save the component
if __name__ == "__main__":
    c = comb_device()
    c.write_gds("comb_device.gds")
    c.show()