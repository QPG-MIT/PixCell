import gdsfactory as gf

@gf.cell
def generate_refined_device():
    """
    Recreates the device geometry with refined proportions.
    Total Footprint: 25um (width) x 10um (height)
    """
    c = gf.Component("refined_device")
    layer = (1, 0)
    
    # --- Proportional Dimensions (Summing to 10um height) ---
    # Total Height (10) = Top Pins (4.5) + Body (4.0) + Bottom Pin (1.5)
    body_w = 20.0 
    body_h = 4.0
    top_pin_total_h = 4.5
    bot_pin_h = 1.5
    
    # 1. Main Body
    # Centered body allows easy placement for top and bottom features
    body = c << gf.components.rectangle(size=(body_w, body_h), layer=layer, centered=True)
    
    # 2. Top Pins (4 units)
    # Proportions: short taper base, very long thin straight segment
    num_pins = 4
    pin_spacing = body_w / num_pins
    pin_w_base = 1.2 # Wider base for the taper
    pin_w_tip = 0.5  # Very thin straight segment
    
    t_h = 1.0 # Short taper height
    s_h = top_pin_total_h - t_h # Longer straight segment
    
    for i in range(num_pins):
        # Calculate X position
        x_pos = -body_w/2 + (i + 0.5) * pin_spacing
        
        # Tapered base of the pin
        taper_ref = c << gf.components.taper(length=t_h, width1=pin_w_base, width2=pin_w_tip, layer=layer)
        taper_ref.rotate(90)
        taper_ref.move((x_pos, body_h/2))
        
        # Long, thin straight part
        straight_ref = c << gf.components.rectangle(size=(pin_w_tip, s_h), layer=layer, centered=True)
        straight_ref.move((x_pos, body_h/2 + t_h + s_h/2))
        
    # 3. Bottom Pin (Single Pointy Taper)
    # Tapering to a very small width for a sharp appearance
    bot_ref = c << gf.components.taper(length=bot_pin_h, width1=1.8, width2=0.2, layer=layer)
    bot_ref.rotate(-90)
    bot_ref.move((0, -body_h/2))
    
    return c

if __name__ == "__main__":
    # Generate the component
    device = generate_refined_device()
    
    # Output GDS file
    device.write_gds("refined_device_layout.gds")
    
    # Print status and verification
    print("--------------------------------------------------")
    print("SUCCESS: 'refined_device_layout.gds' produced.")
    print(f"Final Footprint: {device.xsize:.2f} um (W) x {device.ysize:.2f} um (H)")
    print("Design Strategy: Reduced body height, elongated top/bottom pins.")
    print("--------------------------------------------------")