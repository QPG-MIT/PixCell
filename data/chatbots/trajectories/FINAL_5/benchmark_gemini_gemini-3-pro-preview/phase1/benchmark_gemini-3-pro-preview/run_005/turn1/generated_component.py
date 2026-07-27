import gdsfactory as gf

@gf.cell
def grating_arm(length=10.0, width=0.4, tooth_depth=0.15, pitch=0.28, fill_factor=0.5, layer=(1, 0)):
    """
    Creates a straight waveguide with periodic rectangular teeth on the bottom side.
    """
    c = gf.Component()
    
    # Define a custom cross-section to allow tight integration without validation errors
    xs = gf.cross_section.cross_section(width=width, layer=layer, radius_min=0.5)
    
    # Base waveguide core
    wg = c << gf.components.straight(length=length, cross_section=xs)
    
    # Generate grating teeth
    tooth_length = pitch * fill_factor
    n_teeth = int(length // pitch)
    
    # Define the tooth shape
    tooth_poly = gf.components.rectangle(size=(tooth_length, tooth_depth), layer=layer, centered=True)
    
    # Calculate y-position: Teeth attach to the bottom edge of the waveguide
    # Waveguide spans y=[-width/2, width/2]. Tooth center needs to be offset so it touches the edge.
    y_pos = -width/2 - tooth_depth/2
    
    for i in range(n_teeth):
        # Center x position relative to start
        x_pos = i * pitch + pitch/2
        t = c << tooth_poly
        t.move((x_pos, y_pos))
        
    c.add_port("o1", port=wg.ports["o1"])
    c.add_port("o2", port=wg.ports["o2"])
    return c

@gf.cell
def loop_structure(
    grating_length=10.0,
    wg_width=0.4,
    bend_radius=1.2,
    pitch=0.28,
    tooth_depth=0.15,
    layer=(1, 0)
):
    """
    Assembles one half of the device: Input flare -> Grating Arm -> Hairpin Bend -> Return Arm.
    """
    c = gf.Component()
    
    # Define custom cross-section with relaxed radius constraint for this component
    xs = gf.cross_section.cross_section(width=wg_width, layer=layer, radius_min=0.5)
    
    # 1. Grating Section (Interaction region)
    grating = c << grating_arm(
        length=grating_length,
        width=wg_width,
        tooth_depth=tooth_depth,
        pitch=pitch,
        layer=layer
    )
    
    # 2. Hairpin Loop (180 degree bend)
    # Explicitly pass the cross_section with the low radius_min
    bend = c << gf.components.bend_euler(radius=bend_radius, angle=180, cross_section=xs)
    bend.connect("o1", grating.ports["o2"])
    
    # 3. Return Path (Smooth straight waveguide)
    return_arm = c << gf.components.straight(length=grating_length, cross_section=xs)
    return_arm.connect("o1", bend.ports["o2"])
    
    # 4. Input Flare (Curved entry)
    flare = c << gf.components.bend_euler(radius=bend_radius*1.5, angle=-45, cross_section=xs)
    flare.connect("o1", grating.ports["o1"])
    
    return c

@gf.cell
def contra_dc_device():
    """
    Full device assembly matching the visual topology and footprint.
    """
    c = gf.Component()
    
    # Dimensions derived from image and constraints
    L_grating = 13.0
    W_wg = 0.35
    W_center = 0.15
    Gap = 0.15
    Tooth_depth = 0.15
    Pitch = 0.28
    Radius = 1.2
    
    layer = (1, 0)
    xs_center = gf.cross_section.cross_section(width=W_center, layer=layer, radius_min=0.5)
    
    # 1. Central Bus Waveguide
    bus_len = L_grating + 2.0
    bus = c << gf.components.straight(length=bus_len, cross_section=xs_center)
    bus.center = (0, 0)
    
    # Calculate vertical offset for the loop structures to create the correct gap
    # Center y=0. Grating teeth tip must be at y = W_center/2 + Gap.
    # The Grating Arm is centered at local y=0, with teeth extending down by (W_wg/2 + Tooth_depth).
    # Therefore, the center of the Grating Arm needs to be at:
    y_offset = W_center/2 + Gap + W_wg/2 + Tooth_depth
    
    # 2. Top Loop Structure
    top = c << loop_structure(
        grating_length=L_grating,
        wg_width=W_wg,
        bend_radius=Radius,
        pitch=Pitch,
        tooth_depth=Tooth_depth,
        layer=layer
    )
    # Center the grating region (length 0 to L) horizontally
    top.movex(-L_grating/2)
    top.movey(y_offset)
    
    # 3. Bottom Loop Structure
    # Created identical to top, then rotated 180 degrees
    bot = c << loop_structure(
        grating_length=L_grating,
        wg_width=W_wg,
        bend_radius=Radius,
        pitch=Pitch,
        tooth_depth=Tooth_depth,
        layer=layer
    )
    bot.rotate(180)
    
    # Align Bottom Structure (Symmetric placement)
    bot.movex(L_grating/2)
    bot.movey(-y_offset)
    
    return c

if __name__ == "__main__":
    device = contra_dc_device()
    device.write_gds("contra_dc.gds")
    device.show()