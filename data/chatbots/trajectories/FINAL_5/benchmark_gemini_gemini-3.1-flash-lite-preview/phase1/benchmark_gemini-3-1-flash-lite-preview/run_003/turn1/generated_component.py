import gdsfactory as gf

@gf.cell
def grating_arm(
    length=15.0, 
    waveguide_width=0.5, 
    teeth_width=0.15, 
    teeth_gap=0.15, 
    teeth_length=0.3
):
    """
    Creates one arm of the device with a custom cross-section 
    that allows for tight bend radii.
    """
    c = gf.Component()
    
    # FIX: Define a custom cross-section with a small radius_min
    # to allow the 2.0um bend radius
    xs = gf.cross_section.cross_section(
        width=waveguide_width, 
        layer=(1, 0),
        radius_min=1.0  # Allows bends down to 1.0um
    )
    
    # 1. Straight Section (Waveguide)
    straight = c << gf.components.straight(length=length, cross_section=xs)
    
    # 2. Add Grating Teeth (Manual loop for compatibility)
    num_teeth = int(length / (teeth_width + teeth_gap))
    tooth_template = gf.components.rectangle(size=(teeth_width, teeth_length), layer=(1, 0))
    
    start_x = -(num_teeth * (teeth_width + teeth_gap)) / 2 + (teeth_width / 2)
    
    for i in range(num_teeth):
        tooth = c << tooth_template
        x_pos = start_x + (i * (teeth_width + teeth_gap))
        # Place teeth slightly offset from the waveguide center
        y_pos = (waveguide_width / 2) + (teeth_length / 2)
        tooth.move((x_pos, y_pos))
    
    # 3. U-Bend (180 degree)
    # Using the custom cross-section 'xs'
    u_bend = c << gf.components.bend_euler(radius=2.0, angle=180, cross_section=xs)
    u_bend.connect("o1", straight.ports["o2"])
    
    # 4. Curved Tail
    tail = c << gf.components.bend_euler(radius=2.0, angle=-45, cross_section=xs)
    tail.connect("o1", straight.ports["o1"])
    
    return c

@gf.cell
def device():
    """
    Assembles the final symmetric device.
    """
    c = gf.Component()
    
    # Create top and bottom arms
    arm_top = c << grating_arm()
    arm_bottom = c << grating_arm()
    
    # Mirror the bottom arm for symmetry
    arm_bottom.mirror_y()
    
    # Align the components
    # Spacing selected to match the tight appearance of the device
    arm_top.movey(1.5)
    arm_bottom.movey(-1.5)
    
    return c

if __name__ == "__main__":
    c = device()
    c.write_gds("device.gds")
    print("Device generated successfully with custom radius constraints.")