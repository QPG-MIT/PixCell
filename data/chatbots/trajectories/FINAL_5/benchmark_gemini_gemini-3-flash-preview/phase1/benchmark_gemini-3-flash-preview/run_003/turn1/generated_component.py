import gdsfactory as gf

@gf.cell
def asymmetric_grating_sensor():
    """
    Recreates the device geometry from the image using parametric primitives.
    Total footprint: 18.24 um x 0.7 um.
    
    Structure:
    - Central straight waveguide.
    - Two symmetric arms (top-left shifted, bottom-right shifted).
    - Each arm: Curved tail -> Straight Grating -> 180 Bend -> Tapered Return.
    """
    c = gf.Component("asymmetric_grating_sensor")

    # --- Parameters ---
    # Define a cross-section with a very small radius_min to allow the compact U-bends
    w = 0.05  
    xs = gf.cross_section.cross_section(width=w, layer=(1, 0), radius_min=0.01)
    
    # Targeted footprint
    target_w = 18.24
    target_h = 0.7
    
    # Internal proportions
    comb_len = 9.0
    taper_len = 5.0
    tail_r = 4.0
    tail_angle = 30
    num_teeth = 50
    gap_internal = 0.07 # Gap between comb and return path
    gap_center = 0.06   # Gap between comb and central bar

    def make_arm():
        """Creates one asymmetric arm assembly."""
        arm = gf.Component()
        
        # 1. Main spine (straight waveguide)
        spine = arm << gf.components.straight(length=comb_len, cross_section=xs)
        
        # 2. Grating teeth (facing 'inward')
        tw, th = 0.05, 0.06
        for i in range(num_teeth):
            tooth = arm << gf.components.rectangle(size=(tw, th), layer=(1, 0))
            tooth.x = i * (comb_len / num_teeth) + tw / 2
            tooth.ymax = -w / 2  # Attached to the bottom of the spine
            
        # 3. 180-degree U-turn bend
        # Radius is half of (width + gap) to maintain constant spacing
        bend_r = (w + gap_internal) / 2
        bend = arm << gf.components.bend_circular(radius=bend_r, angle=180, cross_section=xs)
        bend.connect("o1", spine.ports["o2"])
        
        # 4. Return waveguide
        ret_straight = arm << gf.components.straight(length=comb_len - 2.5, cross_section=xs)
        ret_straight.connect("o1", bend.ports["o2"])
        
        # 5. Tapered end
        tip = arm << gf.components.taper(length=taper_len, width1=w, width2=0.001, layer=(1,0))
        tip.connect("o1", ret_straight.ports["o2"])
        
        # 6. Input tail (euler bend for smooth transition)
        tail = arm << gf.components.bend_euler(radius=tail_r, angle=tail_angle, cross_section=xs)
        tail.mirror() # Flip so it curves away from the center
        tail.connect("o1", spine.ports["o1"])
        
        return arm

    # --- Assembly ---
    
    # 1. Central straight waveguide
    center_wg = c << gf.components.straight(length=14.5, cross_section=xs)
    center_wg.x = 0
    center_wg.y = 0
    
    # 2. Add Top Arm (shifted left)
    top_arm = c << make_arm()
    # Vertical offset: center_wg/2 + gap + teeth_height + spine/2
    top_arm.y = (w/2) + gap_center + 0.06 + (w/2)
    top_arm.movex(-1.8)
    
    # 3. Add Bottom Arm (shifted right, 180-deg rotation)
    bot_arm = c << make_arm()
    bot_arm.rotate(180)
    bot_arm.y = -((w/2) + gap_center + 0.06 + (w/2))
    bot_arm.movex(1.8)

    # --- Final Scaling ---
    # Flatten to allow coordinate-based scaling across all internal references
    c.flatten() 
    
    # Calculate current dimensions and scale to exact footprint
    curr_w = c.xsize
    curr_h = c.ysize
    
    sx = target_w / curr_w
    sy = target_h / curr_h
    
    # Apply non-uniform scaling via the geometry reference
    c.scale(sx, sy)
    c.move(origin=c.center, destination=(0, 0))
    
    return c

if __name__ == "__main__":
    device = asymmetric_grating_sensor()
    device.write_gds("final_sensor.gds")
    
    # Verify results
    print(f"Device successfully created.")
    print(f"Final Footprint: {device.xsize:.2f} um x {device.ysize:.2f} um")