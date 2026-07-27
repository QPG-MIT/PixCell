import gdsfactory as gf

@gf.cell
def racetrack_device():
    """
    Recreates the device from the image: A racetrack ring with segmented
    internal rails connected via tapered junctions.
    
    Constraints:
    - Footprint: 3.0 um x 5.5 um
    """
    c = gf.Component("Racetrack_Device")

    # =======================================================================
    # 1. Parameters & Cross-Section
    # =======================================================================
    # Footprint dimensions
    total_length = 5.5
    total_height = 3.0
    
    # Feature sizes
    ring_width = 0.6        # Thickness of the outer ring
    rail_width = 0.5        # Thickness of the inner horizontal bars
    rail_gap_y = 0.4        # Vertical gap between top and bottom rails
    gap_center = 0.3        # Horizontal gap in the exact center
    
    # Geometric calculations
    r_outer = total_height / 2.0  # 1.5 um
    r_center = r_outer - (ring_width / 2.0) # 1.2 um
    l_straight = total_length - total_height # 2.5 um
    
    # Define a custom cross-section. 
    # We explicitly set 'radius' to r_center to override default bend radius constraints.
    xs_ring = gf.cross_section.cross_section(
        width=ring_width, 
        layer=(1, 0),
        radius=r_center 
    )

    # =======================================================================
    # 2. Construct Outer Ring (Racetrack)
    # =======================================================================
    # Create primitives
    bend = gf.components.bend_circular(radius=r_center, angle=180, cross_section=xs_ring)
    straight = gf.components.straight(length=l_straight, cross_section=xs_ring)
    
    # Place Right Bend (Rotated to face inwards)
    b_right = c << bend
    b_right.rotate(180)
    b_right.move((l_straight/2, 0))
    b_right.movey(r_center) # Shift center of curvature to y=0
    
    # Place Left Bend
    b_left = c << bend
    b_left.move((-l_straight/2, -r_center))
    
    # Place Top Straight
    s_top = c << straight
    s_top.movex(-l_straight/2)
    s_top.movey(r_center)
    
    # Place Bottom Straight
    s_bot = c << straight
    s_bot.movex(-l_straight/2)
    s_bot.movey(-r_center)

    # =======================================================================
    # 3. Construct Inner Rails (Rectangles)
    # =======================================================================
    # The rails connect to the ring via a custom taper polygon.
    
    # Calculate rail extents
    rail_start_x = gap_center / 2.0
    # Stop rail before the bend to allow for the taper connection
    taper_length = 0.5 
    rail_end_x = (l_straight / 2.0) - taper_length
    rail_length = rail_end_x - rail_start_x
    
    # Y-offset for the rails
    rail_y_offset = (rail_gap_y / 2.0) + (rail_width / 2.0)
    
    # Create the rectangular rail primitive
    rail_block = gf.components.rectangle(
        size=(rail_length, rail_width), 
        layer=(1, 0), 
        centered=True
    )
    
    # Place 4 rail segments
    # Top Right
    r_tr = c << rail_block
    r_tr.move((rail_start_x + rail_length/2, rail_y_offset))
    # Top Left
    r_tl = c << rail_block
    r_tl.move((-rail_start_x - rail_length/2, rail_y_offset))
    # Bottom Right
    r_br = c << rail_block
    r_br.move((rail_start_x + rail_length/2, -rail_y_offset))
    # Bottom Left
    r_bl = c << rail_block
    r_bl.move((-rail_start_x - rail_length/2, -rail_y_offset))

    # =======================================================================
    # 4. Construct Tapered Junctions (Polygons)
    # =======================================================================
    # Connect the rectangular rails to the inner wall of the ring.
    
    # Coordinates for the connection logic
    x_rail_edge = rail_end_x
    x_ring_edge = l_straight / 2.0
    
    # Y-coords for rail
    y_rail_top = rail_y_offset + rail_width/2
    y_rail_bot = rail_y_offset - rail_width/2
    
    # Y-coord for the inner wall of the ring
    # Ring center y=1.2, width=0.6 -> Inner wall y = 1.2 - 0.3 = 0.9
    y_ring_inner_top = r_center - (ring_width / 2.0)
    
    # Define points for Top-Right connection polygon
    # This creates a shape that widens from the rail to merge into the ring
    points_tr = [
        (x_rail_edge, y_rail_bot),
        (x_rail_edge, y_rail_top),
        (x_ring_edge, y_ring_inner_top),
        (x_ring_edge, y_rail_bot)
    ]
    
    # Add Polygons (mirrored for each quadrant)
    c.add_polygon(points_tr, layer=(1, 0)) # Top Right
    c.add_polygon([(-x, y) for x, y in points_tr], layer=(1, 0)) # Top Left
    c.add_polygon([(x, -y) for x, y in points_tr], layer=(1, 0)) # Bottom Right
    c.add_polygon([(-x, -y) for x, y in points_tr], layer=(1, 0)) # Bottom Left
    
    return c

if __name__ == "__main__":
    device = racetrack_device()
    device.show()
    device.write_gds("racetrack_device.gds")
    
    # Verification using safe property access
    print(f"Device dimensions: {device.xsize:.2f} um x {device.ysize:.2f} um")