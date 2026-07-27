import gdsfactory as gf

@gf.cell
def custom_coupler_device():
    """
    Creates the symmetric multi-finger device exactly matching the target footprint of [25, 10]
    while mimicking the visual proportions of the target image.
    Constructed exclusively using parametric primitives and boolean unions.
    """
    # Key dimensions configured to achieve exact 25x10 footprint
    core_w, core_h = 25.0, 4.5
    top_taper_len, top_straight_len = 2.0, 2.0
    top_w1, top_w2 = 2.0, 0.6
    bot_len, bot_w1, bot_w2 = 1.5, 2.0, 0.8

    # 1. Central Body
    # Spans X: [-12.5, 12.5], Y: [-2.25, 2.25]
    geom = gf.components.rectangle(size=(core_w, core_h), centered=True, layer=(1, 0))

    # 2. Define the Top Finger Component (constructed facing East initially)
    # Taper + Straight Rectangle
    c_tf = gf.Component("top_finger_assembly")
    taper_ref = c_tf << gf.components.taper(length=top_taper_len, width1=top_w1, width2=top_w2, layer=(1, 0))
    straight_ref = c_tf << gf.components.rectangle(size=(top_straight_len, top_w2), centered=True, layer=(1, 0))
    
    # Align the straight section perfectly with the end of the taper
    straight_ref.move((top_taper_len + top_straight_len / 2.0, 0))
    
    # Merge finger parts into a single solid boolean polygon
    tf_solid = gf.boolean(A=taper_ref, B=straight_ref, operation="or", layer=(1, 0))

    # 3. Distribute and Union Top Fingers
    # Exact uniform distribution across the 25um block divides it into 8 equal gaps (pitch = 6.25)
    x_positions = [-9.375, -3.125, 3.125, 9.375]
    
    for x in x_positions:
        # Wrap in a temporary component for spatial transformation prior to boolean evaluation
        wrapper = gf.Component()
        ref = wrapper << tf_solid
        ref.rotate(90)              # Point upwards
        ref.move((x, core_h / 2.0)) # Seat flush on the top edge (Y = +2.25)
        
        # Iteratively union onto the main geometry
        geom = gf.boolean(A=geom, B=wrapper, operation="or", layer=(1, 0))

    # 4. Define and Union Bottom Finger
    # Simple blunt taper pointing downwards
    bot_taper = gf.components.taper(length=bot_len, width1=bot_w1, width2=bot_w2, layer=(1, 0))
    
    wrapper_bot = gf.Component()
    ref_bot = wrapper_bot << bot_taper
    ref_bot.rotate(-90)               # Point downwards
    ref_bot.move((0, -core_h / 2.0))  # Seat flush on the bottom edge (Y = -2.25)
    
    # Final boolean union
    geom = gf.boolean(A=geom, B=wrapper_bot, operation="or", layer=(1, 0))

    return geom

if __name__ == "__main__":
    # Render and output to GDS
    c = custom_coupler_device()
    c.write_gds("custom_coupler_device.gds")