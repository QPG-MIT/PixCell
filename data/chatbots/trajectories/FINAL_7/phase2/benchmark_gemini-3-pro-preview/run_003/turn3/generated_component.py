import gdsfactory as gf

@gf.cell
def device_refined_v2():
    """
    Refined recreation of the racetrack device matching the original image geometry.
    
    Adjustments based on visual analysis:
    1.  Reduced hole width slightly to match the thicker rail proportions of the original.
    2.  Elongated the 'taper' section of the hole polygon to create a smoother, 
        more aerodynamic transition into the bend.
    
    Footprint constraint: 3.0um x 5.5um.
    """
    c = gf.Component()
    
    # =======================================================================
    # 1. Define Parameters
    # =======================================================================
    # External Constraints
    total_height = 3.0
    total_length = 5.5
    
    # Internal Geometries
    track_width = 0.8  # Width of the main racetrack ring
    
    # Derived Dimensions
    # R_outer = 1.5um (half of height). 
    # Path radius (center) is R_outer - half_width
    r_center = (total_height / 2.0) - (track_width / 2.0)  # 1.1um
    
    # Straight length = Total Length - 2 * Height_Radius
    # 5.5 - 3.0 = 2.5um
    l_straight = total_length - total_height 
    
    layer_wg = (1, 0)
    xs = gf.cross_section.cross_section(width=track_width, layer=layer_wg)

    # =======================================================================
    # 2. Create the Racetrack Body (Base)
    # =======================================================================
    # Create the solid racetrack first in a temporary container
    c_body = gf.Component("body_base")
    p = gf.Path()
    
    # Path construction (Bottom Straight -> Right Turn -> Top Straight -> Left Turn)
    p.append(gf.path.straight(length=l_straight))
    p.append(gf.path.arc(radius=r_center, angle=180))
    p.append(gf.path.straight(length=l_straight))
    p.append(gf.path.arc(radius=r_center, angle=180))
    
    # Extrude the path
    body_shape = gf.path.extrude(p, cross_section=xs)
    ref_body = c_body << body_shape
    
    # Manual Centering:
    # The generated path starts at (0,0) and extends to X=l_straight, Y=2*r_center.
    # Center X is l_straight / 2
    # Center Y is r_center
    center_offset_x = l_straight / 2.0
    center_offset_y = r_center
    ref_body.move((-center_offset_x, -center_offset_y))

    # =======================================================================
    # 3. Create the Tapered "Hole" Geometry
    # =======================================================================
    c_holes = gf.Component("holes_mask")
    
    # Refined Hole Parameters
    # Reduced width (0.4 -> 0.32) to give the rails more visual weight
    hole_width = 0.32      
    gap_center = 0.4       # Solid bridge in the center
    
    # Length calculation:
    # The hole extends from the center gap towards the bend.
    # Dist from center to bend start = 1.25um.
    # Hole starts at x = 0.2um (half gap).
    # Hole ends at tangent point (x=1.25). Max len = 1.05.
    hole_total_len = 1.05
    
    # Taper geometry adjustment
    # Increased taper length ratio for a sleeker transition
    taper_len = 0.65       
    flat_len = hole_total_len - taper_len 
    
    # Define Polygon Points for a Right-Pointing shape
    # Origin (0,0) is at the center of the flat edge (left side)
    p0 = (0, hole_width/2)              # Top Left
    p1 = (flat_len, hole_width/2)       # Top Right (start of taper)
    p2 = (hole_total_len, 0)            # Tip (Rightmost point)
    p3 = (flat_len, -hole_width/2)      # Bottom Right (start of taper)
    p4 = (0, -hole_width/2)             # Bottom Left
    
    points = [p0, p1, p2, p3, p4]
    
    poly_hole = gf.Component("hole_polygon")
    poly_hole.add_polygon(points, layer=layer_wg)
    
    # =======================================================================
    # 4. Place the Holes
    # =======================================================================
    x_start = gap_center / 2.0
    y_pos = r_center
    
    # 1. Top Right: Points Right
    h1 = c_holes << poly_hole
    h1.move((x_start, y_pos))
    
    # 2. Top Left: Points Left (Mirror X)
    h2 = c_holes << poly_hole
    h2.mirror(p1=(0,0), p2=(0,1)) 
    h2.move((-x_start, y_pos))
    
    # 3. Bottom Right: Points Right
    h3 = c_holes << poly_hole
    h3.move((x_start, -y_pos))
    
    # 4. Bottom Left: Points Left (Mirror X)
    h4 = c_holes << poly_hole
    h4.mirror(p1=(0,0), p2=(0,1))
    h4.move((-x_start, -y_pos))

    # =======================================================================
    # 5. Boolean Subtraction
    # =======================================================================
    # Subtract the mask (c_holes) from the body (c_body)
    final_shape = gf.boolean(
        A=c_body,
        B=c_holes,
        operation="not",
        layer=layer_wg
    )
    
    c << final_shape
    return c

if __name__ == "__main__":
    device = device_refined_v2()
    device.write_gds("device_refined_v2.gds")
    print(f"GDS file written: device_refined_v2.gds")