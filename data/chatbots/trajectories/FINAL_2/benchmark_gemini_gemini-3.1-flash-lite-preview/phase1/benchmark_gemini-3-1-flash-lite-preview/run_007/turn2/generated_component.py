import gdsfactory as gf

@gf.cell
def create_silhouette():
    """
    Recreates the exact silhouette using rectangles and 
    boolean operations to fuse them into a single polygon.
    """
    c = gf.Component("silhouette")
    layer = (1, 0)
    
    # 1. Main Body (centered)
    # Based on the 25um width constraint, we keep the main block 25um wide
    body = gf.components.rectangle(size=(25, 4), layer=layer, centered=True)
    
    # 2. Define the 'Finger'
    # The image shows these as rectangles, not tapered
    finger_size = (3, 3) # Width and height of the protrusions
    finger = gf.components.rectangle(size=finger_size, layer=layer, centered=True)
    
    # 3. Create a container for the fingers
    fingers_comp = gf.Component("fingers_container")
    
    # 4. Position the 4 top fingers
    # Placed evenly across the 25um width
    top_x_positions = [-9, -3, 3, 9]
    for x in top_x_positions:
        ref = fingers_comp << finger
        # Y position: (body_height/2) + (finger_height/2) = 2 + 1.5 = 3.5
        ref.move((x, 3.5))
        
    # 5. Position the 1 bottom finger
    ref_bot = fingers_comp << finger
    ref_bot.move((0, -3.5))
    
    # 6. Boolean Operation
    # Merges the body and the finger container into one single shape
    # This removes the internal lines so it's a solid silhouette
    final_shape = gf.boolean(body, fingers_comp, operation="or", layer=layer)
    
    return final_shape

# Generate the device
device = create_silhouette()

# Explicitly save the GDS file
file_path = "silhouette_final.gds"
device.write_gds(file_path)

print(f"Success! GDS file saved to: {file_path}")

# Visualize the file
device.show()