import gdsfactory as gf
import numpy as np

@gf.cell
def create_contra_directional_coupler():
    """
    Creates a contra-directional coupler based on the provided image.

    The device consists of two mirrored arms with Bragg gratings facing each
    other, and a central straight waveguide. The arms are constructed using
    a boolean union of a smooth waveguide backbone and a rectangular grating array.
    """

    # --- Parameters ---
    # These parameters are chosen to visually match the image and get close to
    # the target footprint of [18.24, 0.7] um. The height is interpreted as the
    # center-to-center distance of the grating sections.
    
    # Waveguide and Geometry
    wg_width = 0.25
    center_wg_width = 0.1
    center_to_center_y = 0.7  # Assumed from footprint height
    
    # Left side of the arm
    taper_len_L = 1.5
    straight_len_L = 0.5
    
    # U-Bend
    bend_radius_U = 2.0
    
    # Grating Section
    dbr_len = 11.2
    grating_tooth_length = 0.2  # Protrusion from the waveguide
    grating_tooth_width = 0.1
    grating_period = 0.2
    
    # Right side of the arm
    bend_radius_R = 5.0
    bend_angle_R = -30
    taper_len_R = 2.9

    # --- Component Construction ---

    # Define a custom cross-section for the arms to allow for a small bend radius.
    xs_arm = gf.cross_section.cross_section(width=wg_width, radius=None)


    # 1. Create the backbone of a single arm (the continuous waveguide part)
    # This component will serve as one of the operands for the boolean operation.
    backbone = gf.Component("arm_backbone")
    
    # Define primitive components for the backbone, passing the custom cross-section
    taper_L = gf.components.taper(length=taper_len_L, width1=0.01, width2=wg_width, cross_section=xs_arm)
    straight_L = gf.components.straight(length=straight_len_L, cross_section=xs_arm)
    bend_U = gf.components.bend_euler(radius=bend_radius_U, angle=180, cross_section=xs_arm)
    dbr_straight = gf.components.straight(length=dbr_len, cross_section=xs_arm)
    bend_R = gf.components.bend_euler(radius=bend_radius_R, angle=bend_angle_R, cross_section=xs_arm)
    taper_R = gf.components.taper(length=taper_len_R, width1=wg_width, width2=0.01, cross_section=xs_arm)

    # Assemble the backbone by adding references and connecting their ports sequentially
    r_taper_L = backbone << taper_L
    r_straight_L = backbone << straight_L
    r_bend_U = backbone << bend_U
    r_dbr_straight = backbone << dbr_straight
    r_bend_R = backbone << bend_R
    r_taper_R = backbone << taper_R
    
    r_straight_L.connect("o1", r_taper_L.ports["o2"])
    r_bend_U.connect("o1", r_straight_L.ports["o2"])
    r_dbr_straight.connect("o1", r_bend_U.ports["o2"])
    r_bend_R.connect("o1", r_dbr_straight.ports["o2"])
    r_taper_R.connect("o1", r_bend_R.ports["o2"])

    # 2. Create the grating teeth as an array of rectangles
    # This will be the second operand for the boolean operation.
    n_teeth = int(dbr_len / grating_period)
    tooth = gf.components.rectangle(size=(grating_tooth_width, grating_tooth_length))
    
    teeth = gf.Component("grating_teeth")
    
    # FIX: Manually create the array using a loop instead of add_array.
    # The AttributeError indicates that the add_array method is not available.
    # A for loop adding references is a more robust way to create an array.
    for i in range(n_teeth):
        t_ref = teeth << tooth
        t_ref.x = i * grating_period
    
    # Position the teeth array relative to the backbone's DBR section.
    # The teeth are placed on the 'inner' side (lower y) of the top arm's backbone.
    teeth_center_y = (r_dbr_straight.ymin - grating_tooth_length / 2)
    teeth.center = (r_dbr_straight.center[0], teeth_center_y)

    # 3. Perform a boolean 'or' (union) to combine backbone and teeth into a single arm
    arm = gf.boolean(A=backbone, B=teeth, operation="or", layer=(1, 0))
    
    # --- Final Device Assembly ---
    c = gf.Component("FinalDevice")
    
    # 4. Add and position the top and bottom arms
    y_dbr_in_arm = r_dbr_straight.y # y-center of the DBR section in the original backbone
    
    top_arm = c << arm
    bottom_arm = c << arm
    
    # Move top arm so its DBR section is centered at +center_to_center_y/2
    top_arm.movey((center_to_center_y / 2) - y_dbr_in_arm)
    
    # Mirror the bottom arm across the x-axis and position it so its DBR section
    # is centered at -center_to_center_y/2
    bottom_arm.mirror(p1=(0, 0), p2=(1, 0))
    bottom_arm.movey(-(center_to_center_y / 2) + y_dbr_in_arm)

    # 5. Add the central straight line
    total_length = arm.xsize
    center_wg = c << gf.components.straight(length=total_length, width=center_wg_width)
    
    # Center the final device geometry
    c.flatten() # Flatten to get accurate bbox of the combined shape
    center_wg.center = c.center
    c.center = (0,0)


    return c

# Create an instance of the component for export or viewing
device = create_contra_directional_coupler()

# The script is now complete and defines the component parametrically.
# To generate a GDS file, you would add:
# device.write_gds("contra_dc.gds")