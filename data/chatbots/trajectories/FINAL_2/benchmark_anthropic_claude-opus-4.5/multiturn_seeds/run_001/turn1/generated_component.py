import gdsfactory as gf

@gf.cell
def bottle_crate_device():
    """
    A device resembling four bottles in a crate/carrier with a 
    speech-bubble-style pointer at the bottom.
    Designed to fit within 25 x 10 um footprint.
    """
    c = gf.Component()
    
    # === PARAMETERS ===
    # Main crate body
    body_width = 22
    body_height = 4.5
    
    # Bottle necks
    num_bottles = 4
    neck_base_width = 4.2
    neck_top_width = 2.0
    neck_height = 4.5
    
    # Bottom pointer (speech bubble style)
    pointer_width = 2.0
    pointer_height = 1.0
    
    # === CONSTRUCTION ===
    
    # Main rectangular body, centered horizontally, bottom at y=0
    body_ref = c << gf.components.rectangle(
        size=(body_width, body_height),
        layer=(1, 0),
        centered=False
    )
    body_ref.move((-body_width/2, 0))
    
    # Four tapered bottle necks evenly spaced
    spacing = body_width / num_bottles
    for i in range(num_bottles):
        x_center = -body_width/2 + spacing/2 + i * spacing
        
        # Create trapezoid vertices for each bottle neck
        # (wider at base, narrower at top)
        vertices = [
            (x_center - neck_base_width/2, body_height),      # bottom-left
            (x_center + neck_base_width/2, body_height),      # bottom-right
            (x_center + neck_top_width/2, body_height + neck_height),  # top-right
            (x_center - neck_top_width/2, body_height + neck_height)   # top-left
        ]
        c.add_polygon(vertices, layer=(1, 0))
    
    # Downward-pointing triangle at bottom center
    pointer_vertices = [
        (-pointer_width/2, 0),      # left corner at body bottom
        (pointer_width/2, 0),       # right corner at body bottom
        (0, -pointer_height)        # point extending downward
    ]
    c.add_polygon(pointer_vertices, layer=(1, 0))
    
    return c


if __name__ == "__main__":
    # Create the device
    device = bottle_crate_device()
    
    # Display info
    print(f"Device bounding box: {device.bbox}")
    print(f"Device size: {device.bbox[1][0] - device.bbox[0][0]:.1f} x {device.bbox[1][1] - device.bbox[0][1]:.1f} um")
    
    # Save to GDS file
    device.write_gds("bottle_crate_device.gds")
    print("Saved to bottle_crate_device.gds")