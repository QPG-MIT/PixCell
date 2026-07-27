import gdsfactory as gf

@gf.cell
def make_horn(width_max=108.0, width_min=82.0, height=1.25, layer=(1, 0)):
    """
    Creates an hourglass structure with internal horizontal slits.
    The side rails connect the bars, following a concave circular arc.
    """
    c = gf.Component()
    
    # 1. Create the base hourglass solid body
    # We use a rectangle and subtract two circles to create concave side cuts.
    dx = (width_max - width_min) / 2.0
    dy = height / 2.0
    # Calculate radius for a circular arc passing through (w_min/2, 0) and (w_max/2, dy)
    radius = (dx**2 + dy**2) / (2 * dx)
    x_center = radius + width_min / 2.0
    
    rect = gf.components.rectangle(size=(width_max, height), layer=layer, centered=True)
    
    cutouts = gf.Component()
    # Place circles to carve out the waist
    ref_l = cutouts << gf.components.circle(radius=radius, layer=layer)
    ref_l.movex(-x_center)
    ref_r = cutouts << gf.components.circle(radius=radius, layer=layer)
    ref_r.movex(x_center)
    
    # Boolean subtraction to get the hourglass profile
    body = gf.boolean(A=rect, B=cutouts, operation="not", layer=layer)
    
    # 2. Create the internal slits (white space)
    # To leave vertical side rails, the slit width must be slightly less than width_min.
    slit_w = width_min - 2.0 
    slit_h = 0.12  # Height of the gap between bars
    
    slits_geom = gf.Component()
    # We place 4 slits to define 5 horizontal black bars
    # Adjust y-positions to leave thicker segments at the top and bottom of the horn
    for y_pos in [-0.38, -0.13, 0.13, 0.38]:
        s_ref = slits_geom << gf.components.rectangle(size=(slit_w, slit_h), layer=layer, centered=True)
        s_ref.movey(y_pos)
        
    # Subtract slits from the hourglass body
    horn_final = gf.boolean(A=body, B=slits_geom, operation="not", layer=layer)
    c.add_ref(horn_final)
    return c

@gf.cell
def recreate_device():
    """
    Assembles the device within the 120um x 4um footprint constraint.
    """
    c = gf.Component("accurate_device")
    LAYER = (1, 0)
    W_TOTAL = 120.0
    
    # --- Central Section: 5 Long Straight Bars ---
    # Footprint width is 120. Bars are thin and spaced.
    bar_h = 0.08
    gap_h = 0.1
    # Total center height: 5*0.08 + 4*0.1 = 0.8um
    for i in range(5):
        y = (i - 2) * (bar_h + gap_h)
        # Store reference and then transform to avoid 'locked cell' errors
        rect_ref = c << gf.components.rectangle(size=(W_TOTAL, bar_h), layer=LAYER, centered=True)
        rect_ref.movey(y)
        
    # --- Top and Bottom Sections: Hourglass Horns ---
    # Help function creates the curved-side segments with rails
    horn_comp = make_horn(width_max=108.0, width_min=84.0, height=1.25, layer=LAYER)
    
    # Vertical placement logic:
    # center_half_height (0.4) + buffer_gap (0.35) + horn_half_height (0.625) = 1.375
    y_offset = 1.375
    
    # Top Horn
    t_horn = c << horn_comp
    t_horn.movey(y_offset)
    
    # Bottom Horn (Mirrored)
    b_horn = c << horn_comp
    b_horn.mirror_y()
    b_horn.movey(-y_offset)
    
    return c

if __name__ == "__main__":
    device = recreate_device()
    
    # Verification of footprint [120, 4]
    print(f"Final Footprint: {device.xsize:.2f}um x {device.ysize:.2f}um")
    
    # Write to GDS
    device.write_gds("improved_device.gds")