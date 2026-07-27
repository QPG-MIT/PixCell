import gdsfactory as gf

@gf.cell
def tapered_mode_converter():
    """
    Recreates the device geometry using GDSFactory primitives.
    
    Structure composition:
    1. Central taper (the needle)
    2. Two outer tapered arms (the wings)
    3. Right-side rectangular block connecting the arms
    """
    c = gf.Component()
    
    # Standard layer definition
    layer = (1, 0)
    
    # 1. Central Taper (The needle)
    # Dimensions: 25um long, tapering from 0.4um to 0.1um
    # We place it centered at y=0.
    central_needle = c << gf.components.taper(length=25, width1=0.4, width2=0.1, layer=layer)
    central_needle.movey(0)

    # 2. Outer Arms (The wings)
    # We use tapers for the arms to achieve the "flare" effect (widening towards the right)
    # Length is 35um (to meet the right-hand block).
    # Width1=0.35 (left), Width2=0.6 (right flare)
    top_arm = c << gf.components.taper(length=35, width1=0.35, width2=0.6, layer=layer)
    bottom_arm = c << gf.components.taper(length=35, width1=0.35, width2=0.6, layer=layer)
    
    # Vertical positioning to create the central gap
    # Y-offset is set to create a ~0.2um gap from the central needle
    top_arm.movey(0.55)
    bottom_arm.movey(-0.55)

    # 3. Right-side Connection Block
    # The arms connect into this rectangular block.
    # Length=5um (from x=35 to x=40), Width=1.7um (total device footprint height)
    right_block = c << gf.components.rectangle(size=(5, 1.7), layer=layer)
    
    # Move to x=35, y=centered (offset by -0.85 to align the center of the rect with 0)
    right_block.move((35, -0.85))

    return c

# Generate and visualize/save the component
device = tapered_mode_converter()

# To verify dimensions and export:
# device.show() # Opens in KLayout
device.write_gds("tapered_device.gds")