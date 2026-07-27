import gdsfactory as gf

@gf.cell
def racetrack_device():
    """
    Recreates the device geometry:
    - Racetrack outer ring (footprint 5.5 x 3.0 um)
    - Inner horizontal rails with tapered connections to the ring
    - Central gap
    """
    c = gf.Component("Racetrack_Device")

    # =======================================================================
    # 1. Dimensions
    # =======================================================================
    # Target Footprint
    L_total = 5.5
    H_total = 3.0
    
    # Geometry parameters estimated from image
    W_ring = 0.5           # Width of the outer waveguide ring
    W_rail = 0.5           # Width of the inner rail arms
    gap_center = 0.4       # Horizontal gap between left and right arms
    gap_rail_y = 0.5       # Vertical gap between top and bottom arms
    
    # Derived parameters
    # Radius of outer edge = H / 2 = 1.5
    R_outer = H_total / 2.0
    # Radius of center of ring waveguide (Critical for bend primitives)
    R_center = R_outer - (W_ring / 2.0) # 1.25
    # Inner radius of ring (Boundary for the tapered connection)
    R_inner = R_outer - W_ring # 1.0
    
    # Length of straight section
    L_straight = L_total - H_total # 2.5
    half_L = L_straight / 2.0 # 1.25
    
    # Rail vertical coordinates
    # Inner edge of top arm
    y_rail_inner = gap_rail_y / 2.0 # 0.25
    # Outer edge of top arm
    y_rail_outer = y_rail_inner + W_rail # 0.75
    
    # Rail horizontal coordinates
    x_start = gap_center / 2.0 # 0.2
    # The taper starts somewhat before the bend (visual estimate)
    x_taper_start = 0.75 
    # The taper ends at the start of the bend (merging into the ring)
    x_merge = half_L # 1.25

    # =======================================================================
    # 2. Outer Ring Generation
    # =======================================================================
    # We define a cross-section with the specific radius to avoid auto-correction errors
    xs_ring = gf.cross_section.cross_section(
        width=W_ring, 
        radius=R_center, 
        layer=(1, 0)
    )
    
    # Primitives
    bend = gf.components.bend_circular(radius=R_center, angle=180, cross_section=xs_ring)
    straight = gf.components.straight(length=L_straight, cross_section=xs_ring)
    
    # Add Top Straight
    s_top = c << straight
    s_top.move((-half_L, R_center))
    
    # Add Bottom Straight
    s_bot = c << straight
    s_bot.move((-half_L, -R_center))
    
    # Add Right Bend
    # Mirror X: (0,0) East -> (0, -2R) West (Curves down)
    b_right = c << bend
    b_right.mirror(p1=(0,0), p2=(1,0))
    b_right.move((half_L, R_center))
    
    # Add Left Bend
    # Mirror X then Y: Curves down and flipped to the left side
    b_left = c << bend
    b_left.mirror(p1=(0,0), p2=(1,0)) # Curves down
    b_left.mirror(p1=(0,0), p2=(0,1)) # Mirror Y
    b_left.move((-half_L, R_center))

    # =======================================================================
    # 3. Inner Rail Generation (Polygons)
    # =======================================================================
    # We use polygons to define the specific tapered shape connecting the rail to the ring.
    
    # Top Right Arm Polygon Points (Clockwise order)
    points_TR = [
        (x_start, y_rail_inner),        # Bottom Left corner of arm
        (x_start, y_rail_outer),        # Top Left corner of arm
        (x_taper_start, y_rail_outer),  # Start of outer taper
        (x_merge, R_inner),             # Merge point (Inner wall of ring)
        (x_merge, y_rail_inner),        # End of bottom straight
        (x_taper_start, y_rail_inner)   # Bottom taper start (straight line)
    ]
    
    # Create the 4 symmetric arms
    # Top Right
    c.add_polygon(points_TR, layer=(1, 0))
    
    # Top Left (Mirror X coordinates)
    points_TL = [(-x, y) for x, y in points_TR]
    c.add_polygon(points_TL, layer=(1, 0))
    
    # Bottom Right (Mirror Y coordinates)
    points_BR = [(x, -y) for x, y in points_TR]
    c.add_polygon(points_BR, layer=(1, 0))
    
    # Bottom Left (Mirror X and Y coordinates)
    points_BL = [(-x, -y) for x, y in points_TR]
    c.add_polygon(points_BL, layer=(1, 0))

    return c

if __name__ == "__main__":
    device = racetrack_device()
    device.show()
    device.write_gds("racetrack_device.gds")
    
    # Output dimensions for verification
    print(f"Device width: {device.xsize:.3f} um")
    print(f"Device height: {device.ysize:.3f} um")