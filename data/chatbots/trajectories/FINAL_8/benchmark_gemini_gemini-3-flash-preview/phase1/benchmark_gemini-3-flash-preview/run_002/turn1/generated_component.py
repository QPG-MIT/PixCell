import gdsfactory as gf

@gf.cell
def create_mirrored_device():
    """
    Recreates the device geometry from the image.
    Footprint: 120.0 um x 4.0 um.
    """
    c = gf.Component("device_layout")
    layer = (1, 0)
    
    # 1. Middle Section: 5 Long horizontal waveguides
    # These span the full 120um width.
    middle_line_width = 0.05
    middle_line_pitch = 0.12
    middle_rect = gf.components.rectangle(size=(120, middle_line_width), layer=layer, centered=True)
    
    for i in range(5):
        y_offset = (i - 2) * middle_line_pitch
        ref = c << middle_rect
        ref.movey(y_offset)

    # 2. Parametric construction of the "Wing" (top/bottom bracket)
    def make_wing():
        wing = gf.Component()
        
        # Horizontal parts (length 100um)
        # Thick base bar
        base_bar = gf.components.rectangle(size=(100, 0.5), layer=layer, centered=True)
        b_ref = wing << base_bar
        b_ref.movey(0.7) # Positioned above center
        
        # 4 Thin bars above the base
        thin_bar = gf.components.rectangle(size=(100, 0.05), layer=layer, centered=True)
        for i in range(4):
            t_ref = wing << thin_bar
            t_ref.movey(1.1 + i * 0.2)
            
        # Vertical boundary bars (Double bars on each side)
        # Height roughly 1.5um to cover the stack
        v_bar = gf.components.rectangle(size=(0.1, 1.4), layer=layer, centered=True)
        
        # Positions for double bars on left and right
        x_positions = [-50.5, -49.0, 49.0, 50.5]
        for x in x_positions:
            v_ref = wing << v_bar
            v_ref.movex(x).movey(1.1)
            
        # We use gf.boolean to merge these primitives into a single geometry
        # This ensures the internal overlaps are cleaned up
        merged_wing = gf.boolean(A=wing, B=wing, operation="or", layer=layer)
        return merged_wing

    # 3. Assemble and Mirror
    wing_component = make_wing()
    
    # Place Top Wing
    c << wing_component
    
    # Place Bottom Wing by mirroring a reference
    bottom_ref = c << wing_component
    bottom_ref.mirror(p1=(0, 0), p2=(1, 0)) # Mirror across X-axis

    return c

if __name__ == "__main__":
    # Create the component
    device = create_mirrored_device()
    
    # SAVE THE GDS FILE
    # This creates 'device_output.gds' in your current script directory
    file_path = "device_output.gds"
    device.write_gds(file_path)
    
    print(f"GDS file successfully produced: {file_path}")
    
    # Optional: Open in viewer if installed
    # device.show()