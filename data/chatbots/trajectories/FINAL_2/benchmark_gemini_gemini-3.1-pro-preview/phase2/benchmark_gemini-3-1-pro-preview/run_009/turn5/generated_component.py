import gdsfactory as gf

@gf.cell
def fork_device():
    """Creates the parametric fork/comb structure with a 25x10 footprint."""
    c = gf.Component("fork_device")
    
    layer = (1, 0)
    
    # --- Adjusted Proportions & Constraints ---
    # The footprint MUST be bounded within 25um (width) x 10um (height).
    # Based on a pixel analysis of the target image, the visual proportions
    # assume an aspect ratio stretch when rendered in this constrained bounding box.
    # The following dimensions are reverse-engineered to perfectly recreate the target 
    # visual when scaled to fit exactly within a 25x10 area.
    
    body_width = 25.0
    body_height = 5.0
    
    # The body is vertically offset to allow room for the long tines above and short nozzle below,
    # keeping the overall bounding box centered exactly between Y=-5.0 and Y=5.0
    body_y_center = -1.25 
    
    # Tine parameters (Thinner base and straight sections to match the elegant target look)
    taper_len = 2.45
    straight_len = 1.30
    tine_base_w = 2.1
    tine_top_w = 1.1
    
    # The target image displays a distinct asymmetry (tines are shifted left relative to the body).
    # These exact coordinates replicate that visual characteristic.
    tine_x_positions = [-9.2, -3.9, 1.4, 6.7]
    
    # Nozzle parameters
    nozzle_len = 1.25
    nozzle_base_w = 2.6
    nozzle_tip_w = 0.7
    nozzle_x = -0.3 # Replicates the slight off-center alignment seen in the target

    # 1. Main Rectangular Body
    body = gf.components.rectangle(size=(body_width, body_height), layer=layer, centered=True)
    b_ref = c << body
    b_ref.move((0, body_y_center))

    # Calculate exact top and bottom Y coordinates for precise attachment
    body_top_y = body_y_center + (body_height / 2)
    body_bottom_y = body_y_center - (body_height / 2)

    # 2. Top Tines (Constructed with a taper base and a straight rectangular tip)
    tine_taper = gf.components.taper(
        length=taper_len, 
        width1=tine_base_w, 
        width2=tine_top_w
    )
    
    tine_straight = gf.components.rectangle(
        size=(tine_top_w, straight_len), 
        layer=layer, 
        centered=True
    )
    
    for x in tine_x_positions:
        # Place the tapering base
        t_ref = c << tine_taper
        t_ref.rotate(90) # Standard taper faces X+, rotate to face Y+
        # Align wide base ('o1') to the exact top edge of the body
        t_ref.move((x, body_top_y))
        
        # Place the straight rectangular top seamlessly above the taper
        s_ref = c << tine_straight
        # Move rectangle so its bottom edge exactly touches the top of the taper
        s_ref.move((x, body_top_y + taper_len + (straight_len / 2)))

    # 3. Bottom Nozzle
    nozzle = gf.components.taper(
        length=nozzle_len,
        width1=nozzle_base_w,
        width2=nozzle_tip_w
    )
    
    n_ref = c << nozzle
    n_ref.rotate(-90) # Rotate to face Y-
    # Align wide base ('o1') to the exact bottom edge of the body
    n_ref.move((nozzle_x, body_bottom_y))

    return c

if __name__ == "__main__":
    # Create the device
    device = fork_device()
    
    # Save the geometry to a GDS file
    device.write_gds("fork_device.gds")