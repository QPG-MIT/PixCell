import gdsfactory as gf

@gf.cell
def custom_clover():
    """
    Creates a clover/star geometry by merging two crossed ellipses 
    and four rectangular tips into a single, seamless polygon.
    """
    # 1. Define dimensions (total span ~4.7um)
    # Ellipse radii: 2.1um x 0.6um
    r_major = 2.1
    r_minor = 0.6
    
    # 2. Create base primitives
    h_ellipse = gf.components.ellipse(radii=(r_major, r_minor), layer=(1, 0))
    v_ellipse = gf.components.ellipse(radii=(r_minor, r_major), layer=(1, 0))
    tip_h = gf.components.rectangle(size=(0.4, 0.3), centered=True, layer=(1, 0))
    tip_v = gf.components.rectangle(size=(0.3, 0.4), centered=True, layer=(1, 0))

    # 3. Create the core cross by unioning the two ellipses
    core = gf.boolean(h_ellipse, v_ellipse, operation="or", layer=(1, 0))
    
    # 4. Sequentially union the four tips to the core
    # We define positions for the tips
    tips_data = [
        (tip_h, (r_major, 0)),      # Right
        (tip_h, (-r_major, 0)),     # Left
        (tip_v, (0, r_major)),      # Top
        (tip_v, (0, -r_major))      # Bottom
    ]
    
    # Start with the core
    final_shape = core
    
    # Union each tip into the shape
    for tip_comp, pos in tips_data:
        # Create a reference for the tip at the desired position
        # We need to turn the tip component into a boolean-ready object
        # by creating a new component with the tip placed correctly
        temp_c = gf.Component()
        ref = temp_c << tip_comp
        ref.move(pos)
        
        # Merge the current progress with the new tip
        final_shape = gf.boolean(final_shape, temp_c, operation="or", layer=(1, 0))
        
    return final_shape

# Generate the component
device = custom_clover()

if __name__ == "__main__":
    # Save to GDS
    device.write_gds("clover_shape.gds")
    # Display
    device.show()