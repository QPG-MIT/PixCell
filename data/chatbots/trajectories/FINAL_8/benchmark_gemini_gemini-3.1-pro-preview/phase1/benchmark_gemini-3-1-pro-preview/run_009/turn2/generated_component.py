import gdsfactory as gf

@gf.cell
def clipped_coupler_array():
    """
    Recreates the multi-waveguide coupler array with outer bends
    clipped exactly to the 120.0 x 4.0 footprint.
    
    The geometry uses large-radius concentric arcs to recreate the 
    sweeping curves seen in the target image, which are then boolean-clipped 
    by the exact footprint boundaries.
    """
    c_raw = gf.Component("raw_array")

    # Dimensions
    L_total = 120.0
    L_straight = 80.0
    x_start = L_straight / 2.0  # 40.0
    
    # --- 1. Central Group (5 parallel straight waveguides) ---
    y_center = [-0.32, -0.16, 0.0, 0.16, 0.32]
    w_center = 0.06
    
    for y in y_center:
        xs = gf.cross_section.cross_section(width=w_center, layer=(1, 0))
        # Extended slightly beyond footprint to ensure clean boolean cuts at the ends
        wg = c_raw << gf.components.straight(length=L_total + 4.0, cross_section=xs)
        wg.move((-(L_total + 4.0)/2, y))


    # --- 2. Top Group (Bends Upwards) ---
    # Defines the vertical starting positions (straight sections) and widths 
    # for the elements matching the visual proportions of the original image.
    top_elements = [
        (0.75, 0.60),  # Inner thick band
        (1.18, 0.06),  # Thin line 1
        (1.34, 0.06),  # Thin line 2
        (1.50, 0.06),  # Thin line 3
        (1.66, 0.06),  # Thin line 4
        (1.86, 0.14),  # Outer thick line
    ]
    
    # A single shared center of curvature Y-coordinate far outside the device
    # mathematically guarantees all paths curve perfectly concentrically
    # and spread out correctly when hitting the top boundary.
    y_c = 130.0

    for y_str, w in top_elements:
        R = y_c - y_str  # Concentric radius calculation
        xs = gf.cross_section.cross_section(width=w, layer=(1, 0))
        
        # Right Side Segment
        p_r = gf.Path()
        p_r.append(gf.path.straight(length=x_start))
        p_r.append(gf.path.arc(radius=R, angle=90))
        p_r.append(gf.path.straight(length=20.0)) # Tail ensures crossing the top boundary
        
        comp_r = gf.path.extrude(p_r, cross_section=xs)
        wg_tr = c_raw << comp_r
        wg_tr.move((0, y_str))
        
        # Left Side Segment (Mirrored perfectly across center Y-axis)
        wg_tl = c_raw << comp_r
        wg_tl.move((0, y_str))
        wg_tl.mirror(p1=(0,0), p2=(0,1))


    # --- 3. Bottom Group (Bends Downwards) ---
    for y_str, w in top_elements:
        # Use the exact same radius values to guarantee perfect top/bottom symmetry
        R = y_c - y_str 
        xs = gf.cross_section.cross_section(width=w, layer=(1, 0))
        
        # Right Side Segment (Curves down by using a negative angle)
        p_r = gf.Path()
        p_r.append(gf.path.straight(length=x_start))
        p_r.append(gf.path.arc(radius=R, angle=-90)) 
        p_r.append(gf.path.straight(length=20.0))
        
        comp_r = gf.path.extrude(p_r, cross_section=xs)
        wg_br = c_raw << comp_r
        wg_br.move((0, -y_str)) # Move to symmetric negative Y position
        
        # Left Side Segment (Mirrored)
        wg_bl = c_raw << comp_r
        wg_bl.move((0, -y_str))
        wg_bl.mirror(p1=(0,0), p2=(0,1))


    # --- 4. Precise Boundary Clipping ---
    # Create the rigid bounding box required by the constraints
    bbox = gf.components.rectangle(size=(120.0, 4.0), layer=(1, 0), centered=True)

    # Boolean 'AND' cleanly slices all unbounded tails exactly at the 120x4 perimeter
    clipped_device = gf.boolean(c_raw, bbox, operation="and", layer=(1, 0))

    return clipped_device

if __name__ == "__main__":
    device = clipped_coupler_array()
    device.write_gds("output.gds")