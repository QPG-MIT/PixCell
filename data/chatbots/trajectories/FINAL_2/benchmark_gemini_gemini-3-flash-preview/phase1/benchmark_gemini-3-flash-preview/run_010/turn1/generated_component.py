import gdsfactory as gf

@gf.cell
def recreated_device():
    layer = (1, 0)
    
    # --- Dimensions (Total Height: 10um, Total Width: 25um) ---
    body_w = 25.0
    body_h = 6.0    # Middle section
    top_h = 3.0     # Fingers section
    bot_h = 1.0     # Bottom protrusion section
    
    # 1. Create the Main Body
    # Using centered=True puts the center at (0,0)
    body = gf.components.rectangle(size=(body_w, body_h), layer=layer, centered=True)
    
    # 2. Create Top Fingers Component
    top_part = gf.Component("top_part")
    f_w_base = 2.0
    f_w_tip = 1.0
    f_taper_h = 1.0
    f_straight_h = 2.0 # Total finger height = 3.0
    
    # Define a single finger
    finger = gf.Component("finger_unit")
    # Taper goes along X by default, rotate it to point up (+Y)
    taper = finger << gf.components.taper(length=f_taper_h, width1=f_w_base, width2=f_w_tip, layer=layer)
    taper.rotate(90)
    
    # Straight segment at the tip
    straight = finger << gf.components.straight(length=f_straight_h, 
                                                cross_section=gf.cross_section.cross_section(width=f_w_tip, layer=layer))
    straight.rotate(90)
    straight.movey(f_taper_h)
    
    # Array 4 fingers across the top edge of the body (y = 3.0)
    finger_x_coords = [-9.0, -3.0, 3.0, 9.0]
    for x in finger_x_coords:
        f_ref = top_part << finger
        f_ref.move((x, body_h / 2))
        
    # 3. Create Bottom Protrusion Component
    bot_part = gf.Component("bot_part")
    # Pointing down (-Y)
    bp = bot_part << gf.components.taper(length=bot_h, width1=3.0, width2=1.5, layer=layer)
    bp.rotate(-90)
    bp.movey(-body_h / 2)
    
    # 4. Combine using Boolean Operations
    # We use sequential OR operations to merge the components into a single silhouette
    # Merging Body + Top Fingers
    inter_res = gf.boolean(A=body, B=top_part, operation="or", layer=layer)
    
    # Merging Result + Bottom Protrusion
    final_geom = gf.boolean(A=inter_res, B=bot_part, operation="or", layer=layer)
    
    return final_geom

if __name__ == "__main__":
    # Generate the component
    c = recreated_device()
    
    # Export to GDS
    c.write_gds("device_reproduction.gds")
    
    # Display the result
    c.show()