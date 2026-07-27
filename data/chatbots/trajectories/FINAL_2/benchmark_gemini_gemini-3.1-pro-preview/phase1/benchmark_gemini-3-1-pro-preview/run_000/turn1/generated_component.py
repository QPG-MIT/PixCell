import gdsfactory as gf

@gf.cell
def custom_coupler_device():
    """
    Creates the symmetric multi-finger device matching the target footprint of [25, 10].
    Constructed exclusively using parametric primitives and boolean unions.
    """
    # 1. Central Body
    # To maintain exactly a 25x10 footprint with the top and bottom protrusions, 
    # we allocate 5um height for the central body.
    # X span: [-12.5, 12.5] (25um total width)
    # Y span: [-2.5, 2.5] (5um total height)
    core = gf.components.rectangle(size=(25, 5), centered=True, layer=(1, 0))
    
    # We will accumulate the full geometry into 'device_geom'
    device_geom = core

    # 2. Define the Top Finger Component
    # Composed of a tapered base and a straight section at the tip.
    # Total top finger height = 2.0 (taper) + 1.5 (straight) = 3.5 um.
    top_finger = gf.Component("top_finger")
    
    # Tapered base: 2.0um long, tapering from 2.5um to 1.0um
    taper_base = top_finger << gf.components.taper(length=2.0, width1=2.5, width2=1.0)
    
    # Straight tip: 1.5um long, 1.0um wide
    # Using a rectangle for the straight section, moving it to align with the taper's narrow end.
    straight_tip = top_finger << gf.components.rectangle(size=(1.5, 1.0), centered=True, layer=(1, 0))
    straight_tip.move((2.0 + 0.75, 0))  # 2.0 (taper length) + 0.75 (half of straight length)

    # 3. Place and Union Top Fingers
    # 4 fingers distributed evenly across the 25um width.
    x_positions = [-9.0, -3.0, 3.0, 9.0]
    
    for x in x_positions:
        # Create a temporary component to apply spatial transformations before boolean logic
        f_placement = gf.Component()
        ref = f_placement << top_finger
        ref.rotate(90)          # Point upwards
        ref.move((x, 2.5))      # Sit flush on the top edge of the central body
        
        # Merge the placed finger with the central body
        device_geom = gf.boolean(A=device_geom, B=f_placement, operation="or", layer=(1, 0))

    # 4. Place and Union Bottom Finger
    # Centered downward finger, simply a taper ending at a flat tip.
    # Bottom finger height = 1.5 um.
    bot_placement = gf.Component("bot_finger")
    bot_taper = bot_placement << gf.components.taper(length=1.5, width1=2.5, width2=1.0)
    bot_taper.rotate(-90)       # Point downwards
    bot_taper.move((0, -2.5))   # Sit flush on the bottom edge of the central body
    
    # Merge the bottom finger with the main geometry
    device_geom = gf.boolean(A=device_geom, B=bot_placement, operation="or", layer=(1, 0))

    return device_geom

if __name__ == "__main__":
    # Generate and save the device to GDS
    c = custom_coupler_device()
    c.write_gds("custom_coupler_device.gds")