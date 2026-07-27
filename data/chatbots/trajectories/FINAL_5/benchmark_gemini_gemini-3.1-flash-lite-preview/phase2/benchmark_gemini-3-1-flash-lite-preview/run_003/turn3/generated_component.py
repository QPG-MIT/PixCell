import gdsfactory as gf

# 1. Define the CrossSection with an appropriate radius_min
# This fixes the ValueError because 2.0 <= 5.0 (our bend radius)
xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0), radius_min=2.0)

@gf.cell
def grating_arm(length=20, side="bottom", radius=5.0):
    """
    Creates one arm of the coupler with gratings facing the gap.
    """
    c = gf.Component()
    
    # Straight Section
    wg = c << gf.components.straight(length=length, cross_section=xs)
    
    # Grating Parameters
    tooth_w = 0.2
    tooth_l = 0.3
    period = 0.5
    num_teeth = int(length / period)
    
    # Place teeth on the side facing the gap
    # If side="bottom", teeth are at negative y (bottom of top waveguide)
    # If side="top", teeth are at positive y (top of bottom waveguide)
    y_offset = -(0.5/2 + tooth_l/2) if side == "bottom" else (0.5/2 + tooth_l/2)
    
    for i in range(num_teeth):
        x = (i * period) - (length / 2) + (period/2)
        tooth = c << gf.components.rectangle(size=(tooth_w, tooth_l), layer=(1, 0))
        tooth.center = (x, y_offset)

    # 2. Add Bends
    if side == "bottom":
        # TOP ARM: U-bend on the RIGHT, Curve on the LEFT
        u_bend = c << gf.components.bend_euler(radius=radius, angle=180, cross_section=xs)
        u_bend.connect("o1", wg.ports["o2"])
        
        # Curve away from gap (outward)
        in_bend = c << gf.components.bend_euler(radius=radius, angle=-45, cross_section=xs)
        in_bend.connect("o1", wg.ports["o1"])
        
        c.add_port("o1", port=in_bend.ports["o2"]) 
        c.add_port("o2", port=u_bend.ports["o2"])
    else:
        # BOTTOM ARM: U-bend on the LEFT, Curve on the RIGHT
        u_bend = c << gf.components.bend_euler(radius=radius, angle=-180, cross_section=xs)
        u_bend.connect("o1", wg.ports["o1"])
        
        # Curve away from gap (outward)
        in_bend = c << gf.components.bend_euler(radius=radius, angle=45, cross_section=xs)
        in_bend.connect("o1", wg.ports["o2"])
        
        c.add_port("o1", port=u_bend.ports["o2"])
        c.add_port("o2", port=in_bend.ports["o2"])

    return c

@gf.cell
def device():
    c = gf.Component()
    gap = 0.4
    arm_len = 15
    
    # Add Top Arm
    top = c << grating_arm(length=arm_len, side="bottom", radius=5.0)
    top.movey(gap / 2 + 0.25)
    
    # Add Bottom Arm
    bot = c << grating_arm(length=arm_len, side="top", radius=5.0)
    bot.movey(-(gap / 2 + 0.25))
    
    return c

if __name__ == "__main__":
    c = device()
    c.show()
    c.write_gds("device.gds")
    print("Geometry generated successfully.")