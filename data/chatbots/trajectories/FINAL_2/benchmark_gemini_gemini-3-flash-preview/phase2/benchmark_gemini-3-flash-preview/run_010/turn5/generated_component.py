import gdsfactory as gf

@gf.cell
def recreated_device():
    layer = (1, 0)
    
    # --- Dimensions (Constrained to 25um x 10um footprint) ---
    body_w = 25.0
    body_h = 5.0    
    
    # Fingers (Total height budget = 4.0um)
    f_taper_h = 2.7 
    f_straight_h = 1.3
    f_w_base = 2.2   # Significantly narrowed from previous version
    f_w_tip = 1.2    # Slender tips
    
    # Bottom stub (Total height budget = 1.0um)
    bot_h = 1.0
    bot_w_base = 2.8
    bot_w_tip = 1.0
    
    # Total Height check: 5.0 (body) + 4.0 (fingers) + 1.0 (stub) = 10.0 um
    
    # 1. Create the Main Body
    body = gf.components.rectangle(size=(body_w, body_h), layer=layer, centered=True)
    
    # 2. Create the Top Fingers
    top_part = gf.Component("top_fingers")
    
    # Define single finger unit
    finger = gf.Component("finger_unit")
    # Base taper
    taper = finger << gf.components.taper(length=f_taper_h, width1=f_w_base, width2=f_w_tip, layer=layer)
    taper.rotate(90)
    
    # Straight tip section
    straight = finger << gf.components.straight(length=f_straight_h, 
                                                cross_section=gf.cross_section.cross_section(width=f_w_tip, layer=layer))
    straight.rotate(90)
    straight.movey(f_taper_h)
    
    # Position 4 fingers with wider spacing
    # Spacing is adjusted to leave significant margins on the left/right edges
    finger_x_positions = [-8.5, -2.8, 2.8, 8.5]
    for x in finger_x_positions:
        f_ref = top_part << finger
        f_ref.move((x, body_h / 2))
        
    # 3. Create the Bottom Protrusion (Stub)
    bot_part = gf.Component("bottom_protrusion")
    bp = bot_part << gf.components.taper(length=bot_h, width1=bot_w_base, width2=bot_w_tip, layer=layer)
    bp.rotate(-90)
    bp.movey(-body_h / 2)
    
    # 4. Assembly via Boolean Operations
    # This merges all components into a single continuous shape
    merged_top = gf.boolean(A=body, B=top_part, operation="or", layer=layer)
    final_device = gf.boolean(A=merged_top, B=bot_part, operation="or", layer=layer)
    
    final_device.name = "recreated_device_v5"
    return final_device

if __name__ == "__main__":
    c = recreated_device()
    c.show() 
    c.write_gds("recreated_device_v5.gds")