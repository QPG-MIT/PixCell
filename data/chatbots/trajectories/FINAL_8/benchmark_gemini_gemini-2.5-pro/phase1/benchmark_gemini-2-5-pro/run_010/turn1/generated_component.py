import gdsfactory as gf
import numpy as np

@gf.cell
def create_device():
    """
    Creates the device geometry based on the provided image and footprint.

    This corrected script fixes two critical issues from the original attempt:
    1. It uses `gf.path.smooth` to correctly generate the flared path, avoiding
       the geometric errors caused by improper manual path segment concatenation.
    2. It simplifies and corrects the vertical placement logic for the three
       main components to ensure they are spaced correctly.

    The device is constructed by defining a complex cross-section with five
    parallel stripes and extruding it along two different paths: one straight
    path for the center and one flared S-bend path for the top and bottom sections.
    """
    # 1. Define constants derived from footprint and visual proportions
    DEVICE_WIDTH = 120.0
    
    # Vertical dimensions
    H_STRIPE_BAND = 0.727  # Height of the 5-stripe group
    G_VERTICAL = 0.182     # Gap between stripe bands
    # The vertical displacement of the flared path, set equal to the band height
    DY_PATH_FLARE = H_STRIPE_BAND 
    
    # Horizontal dimensions for the flared path
    L_STRAIGHT_FLARE = 60.0
    DX_BEND_FLARE = (DEVICE_WIDTH - L_STRAIGHT_FLARE) / 2

    # Layer for the geometry
    LAYER = (1, 0)

    # 2. Create the multi-stripe cross-section
    # The stripe band is composed of 5 identical stripes and 4 identical gaps,
    # assuming gap width is equal to stripe width.
    num_stripes = 5
    stripe_width = H_STRIPE_BAND / (2 * num_stripes - 1)
    pitch = 2 * stripe_width
    
    sections = []
    # Center stripe
    sections.append(gf.Section(width=stripe_width, offset=0, layer=LAYER))
    # Add symmetric pairs of stripes
    for i in range(1, 3): # Corresponds to offsets of 1*pitch and 2*pitch
        offset = i * pitch
        sections.append(gf.Section(width=stripe_width, offset=offset, layer=LAYER))
        sections.append(gf.Section(width=stripe_width, offset=-offset, layer=LAYER))
    
    xs_multi_stripe = gf.CrossSection(sections=sections)
    
    # 3. Create the flared component template using a smooth, robust path
    # Define waypoints: starts at (0,0), flares up, straight, flares down to (width, 0)
    points = [
        (0, 0),
        (DX_BEND_FLARE, DY_PATH_FLARE),
        (DX_BEND_FLARE + L_STRAIGHT_FLARE, DY_PATH_FLARE),
        (DEVICE_WIDTH, 0),
    ]

    # gf.path.smooth connects these points with smooth Euler bends.
    # We can provide a hint for the bend radius for better control.
    # A suitable radius can be derived from the s-bend geometry formula.
    bend_radius = (DX_BEND_FLARE**2 + DY_PATH_FLARE**2) / (4 * DY_PATH_FLARE)

    # Create the path and extrude it
    path_flared = gf.path.smooth(points, radius=bend_radius)
    c_flared_template = gf.path.extrude(path_flared, cross_section=xs_multi_stripe)

    # 4. Create the central straight component
    path_straight = gf.path.straight(length=DEVICE_WIDTH)
    c_central = gf.path.extrude(path_straight, cross_section=xs_multi_stripe)

    # 5. Assemble the final device
    c = gf.Component("final_device")

    # Define the vertical separation between the centerlines of the bands
    y_separation = H_STRIPE_BAND + G_VERTICAL

    # Add central band, centered at y=0
    c.add_ref(c_central)

    # Add top band, moved up by y_separation
    top_ref = c.add_ref(c_flared_template)
    top_ref.movey(y_separation)

    # Add bottom band, mirrored across the x-axis and moved down by y_separation
    bottom_ref = c.add_ref(c_flared_template)
    bottom_ref.mirror(p1=(0, 0), p2=(1, 0))
    bottom_ref.movey(-y_separation)
    
    return c

# Create an instance of the device
device = create_device()

# This will generate the GDS file when the script is run.
device.write_gds("output.gds")