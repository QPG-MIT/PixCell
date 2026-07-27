import gdsfactory as gf

@gf.cell
def recreate_device():
    """
    Refined photonic device for Turn 5 (Fixed radius_min and height constraints).
    Focus: Explicit radius_min for nanoscale bends, DBU compliance, and height limit.
    Footprint target: 18.24um x 0.7um
    """
    c = gf.Component("device_turn_5_final_v2")
    
    # --- DIMENSIONS (micrometers) ---
    total_length = 18.24
    layer = (1, 0)
    
    # Widths (Even DBU/nm)
    bus_width = 0.046     
    wg_width = 0.066      
    
    # Radii and Grating - Optimized for 0.7um height constraint
    # Calculation: (Outer needle edge) = y_shift + radius + (wg_width/2)
    u_radius = 0.075      
    num_teeth = 60        
    tooth_w = 0.060       
    tooth_h = 0.080       # Slightly shorter to save vertical space
    gap_bus = 0.024       
    
    backbone_l = 8.5      
    needle_l = 9.0        
    
    # Define Cross-Sections with explicit radius_min for nanoscale geometry
    xs_bus = gf.cross_section.cross_section(width=bus_width, layer=layer, radius_min=0.01)
    xs_arm = gf.cross_section.cross_section(width=wg_width, layer=layer, radius_min=0.01)

    # 1. Central Bus Waveguide
    bus = c << gf.components.straight(length=total_length, cross_section=xs_bus)
    bus.movex(-total_length / 2)

    # 2. Arm Generator Function
    def create_arm():
        arm = gf.Component()
        
        # A. Backbone
        backbone = arm << gf.components.straight(length=backbone_l, cross_section=xs_arm)
        
        # B. Semi-circular U-turn (0.075 radius)
        uturn = arm << gf.components.bend_circular(radius=u_radius, angle=180, cross_section=xs_arm)
        uturn.connect("o1", backbone.ports["o2"])
        
        # C. Return Needle (Straight + Long Taper)
        needle_straight = arm << gf.components.straight(length=needle_l - 3.0, cross_section=xs_arm)
        needle_straight.connect("o1", uturn.ports["o2"])
        
        needle_tip = arm << gf.components.taper(
            length=3.0, width1=wg_width, width2=0.006, layer=layer
        )
        needle_tip.connect("o1", needle_straight.ports["o2"])
        
        # D. Tail Sweep
        tail_bend = arm << gf.components.bend_euler(radius=1.0, angle=45, cross_section=xs_arm)
        tail_bend.connect("o1", backbone.ports["o1"])
        
        tail_taper = arm << gf.components.taper(
            length=3.5, width1=wg_width, width2=0.006, layer=layer
        )
        tail_taper.connect("o1", tail_bend.ports["o2"])
        
        # E. Chunky Gratings
        period = backbone_l / (num_teeth - 1)
        for i in range(num_teeth):
            # Centered=False is default for rectangle; we set x/y manually
            t = arm << gf.components.rectangle(size=(tooth_w, tooth_h), layer=layer)
            t.x = i * period
            t.ymax = -wg_width / 2 # Attach to the bottom of the backbone
            
        return arm

    # 3. Assembly with Point Symmetry
    top_arm = c << create_arm()
    bot_arm = c << create_arm()
    
    # Rotate bottom arm 180 degrees to match point symmetry
    bot_arm.rotate(180)
    
    # Calculate vertical shift
    # y_shift is from center of bus to center of backbone
    y_shift = (bus_width / 2) + gap_bus + tooth_h + (wg_width / 2)
    
    top_arm.movey(y_shift)
    bot_arm.movey(-y_shift)
    
    # Horizontal balance
    top_arm.movex(-backbone_l / 2 + 1.2)
    bot_arm.movex(backbone_l / 2 - 1.2)

    return c

if __name__ == "__main__":
    device = recreate_device()
    device.write_gds("recreated_device_turn5_v2.gds")
    device.show()