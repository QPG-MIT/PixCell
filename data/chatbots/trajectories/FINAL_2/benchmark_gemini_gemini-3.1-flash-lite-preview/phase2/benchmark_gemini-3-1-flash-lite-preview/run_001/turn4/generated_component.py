import gdsfactory as gf
import numpy as np

@gf.cell
def custom_device():
    """
    Creates the device by placing references of the rectangle and tapers
    directly onto the component, avoiding complex boolean operations.
    """
    c = gf.Component()

    # 1. Define and add the main body (25 x 10)
    # Using the specified footprint (centered at 0,0)
    rect = c << gf.components.rectangle(size=(25, 10), centered=True, layer=(1, 0))

    # 2. Define the pillar primitive
    # We create one taper reference that we will reuse
    taper_len = 4
    # width1 is the base (connected to rect), width2 is the tip
    taper_shape = gf.components.taper(length=taper_len, width1=2.5, width2=1.0, layer=(1, 0))

    # 3. Add Top Pillars (4 pillars)
    # We place them at specific X coordinates, along the top edge (y=5)
    # Spacing them across the width of 25um
    top_positions = [-9, -3, 3, 9] 
    
    for x in top_positions:
        ref = c << taper_shape
        ref.rotate(90) # Point upwards
        # The taper base sits on the top edge (y=5). 
        # Note: Depending on the taper definition, we might need a small offset.
        # Placing the reference origin at (x, 5) usually aligns the base to the edge.
        ref.move((x, 5)) 

    # 4. Add Bottom Pillar (1 pillar)
    # Centered at (0, -5)
    ref_bottom = c << taper_shape
    ref_bottom.rotate(-90) # Point downwards
    ref_bottom.move((0, -5))

    return c

# Generate the component
device = custom_device()
device.write_gds("unified_device_v3.gds")

print("Successfully generated unified_device_v3.gds with direct reference placement.")