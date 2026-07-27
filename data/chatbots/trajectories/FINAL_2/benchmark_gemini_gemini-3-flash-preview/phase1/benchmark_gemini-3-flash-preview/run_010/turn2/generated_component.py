import gdsfactory as gf

@gf.cell
def recreated_device():
    layer = (1, 0)
    
    # --- Dimensions (25um wide x 10um high) ---
    body_w = 25.0
    body_h = 6.0
    top_h = 3.0
    bot_h = 1.0
    
    # 1. Create the Main Body
    # We don't flatten this; we use it as-is.
    body = gf.components.rectangle(size=(body_w, body_h), layer=layer, centered=True)
    
    # 2. Create the Top Fingers
    top_part = gf.Component("top_fingers")
    f_w_base = 4.0     # Wide base to match the original
    f_w_tip = 1.8      # Narrower tip
    f_taper_h = 1.8    # Long taper transition
    f_straight_h = 1.2 # Short straight tip
    
    # Define single finger
    finger = gf.Component("finger_unit")
    taper = finger << gf.components.taper(length=f_taper_h, width1=f_w_base, width2=f_w_tip, layer=layer)
    taper.rotate(90)
    
    straight = finger << gf.components.straight(length=f_straight_h, 
                                                cross_section=gf.cross_section.cross_section(width=f_w_tip, layer=layer))
    straight.rotate(90)
    straight.movey(f_taper_h)
    
    # Add 4 fingers. Spacing: center-to-center = 6um.
    finger_x_positions = [-9.0, -3.0, 3.0, 9.0]
    for x in finger_x_positions:
        f_ref = top_part << finger
        f_ref.move((x, body_h / 2))
        
    # 3. Create the Bottom Protrusion
    bot_part = gf.Component("bottom_protrusion")
    bp = bot_part << gf.components.taper(length=bot_h, width1=4.0, width2=1.5, layer=layer)
    bp.rotate(-90)
    bp.movey(-body_h / 2)
    
    # 4. Perform Boolean Operations
    # gf.boolean accepts Component objects directly. It creates a NEW component
    # containing the merged polygons, which avoids the LockedError.
    
    # Merge Body and Top Fingers
    temp_union = gf.boolean(A=body, B=top_part, operation="or", layer=layer)
    
    # Merge result with Bottom Protrusion
    final_device = gf.boolean(A=temp_union, B=bot_part, operation="or", layer=layer)
    
    # Set the name of the final component for the cell cache
    final_device.name = "final_recreated_device"
    
    return final_device

if __name__ == "__main__":
    # Create the component
    c = recreated_device()
    
    # Write to GDS
    c.write_gds("final_device.gds")
    
    # View the result
    c.show()