import gdsfactory as gf

@gf.cell
def grating_waveguide(
    length=40,
    width=0.5,
    period=0.5,
    duty_cycle=0.5,
    corrugation_width=0.3,
    layer=(1, 0)
):
    """
    Creates a straight waveguide with periodic sidewall corrugations.
    """
    c = gf.Component()
    
    # Base waveguide core
    xs = gf.cross_section.cross_section(width=width, layer=layer)
    wg = c << gf.components.straight(length=length, cross_section=xs)
    
    # Add input/output ports from the base waveguide
    c.add_port("o1", port=wg.ports["o1"])
    c.add_port("o2", port=wg.ports["o2"])
    
    # Create the tooth shape (corrugation)
    tooth_w = period * duty_cycle
    tooth_h = width + 2 * corrugation_width
    tooth = gf.components.rectangle(size=(tooth_w, tooth_h), layer=layer, centered=True)
    
    # Array the teeth along the waveguide
    num_periods = int(length / period)
    
    for i in range(num_periods):
        # Calculate position: start from left + offset
        x_pos = -length/2 + (i * period) + (period/2)
        t_ref = c << tooth
        t_ref.move((x_pos, 0))
        
    return c

@gf.cell
def photonic_cdc_device():
    """
    Recreation of the Contra-Directional Coupler device from primitives.
    """
    c = gf.Component()
    
    # --- Parameters ---
    layer = (1, 0)
    width = 0.5
    gap = 0.2
    
    # Adjusted radius to 10.0 to satisfy default CrossSection.radius_min
    bend_radius = 10.0 
    grating_len = 40.0
    return_len = grating_len + 15.0 
    
    # Define cross-section explicitly with the radius we intend to use
    xs = gf.cross_section.cross_section(width=width, layer=layer, radius=bend_radius)
    
    # --- 1. Central Bus ---
    bus_length = grating_len + 4 * bend_radius
    central_bus = c << gf.components.straight(length=bus_length, cross_section=xs)
    central_bus.move(central_bus.center, (0, 0))

    # --- 2. Top Assembly ---
    # Grating Section
    grating_top = c << grating_waveguide(length=grating_len, width=width, layer=layer)
    y_offset = (width/2) + gap + (width/2)
    grating_top.move((0, y_offset))
    
    # 180 degree U-Turn (Right side)
    bend_top_right = c << gf.components.bend_euler(radius=bend_radius, angle=180, cross_section=xs)
    bend_top_right.connect("o1", grating_top.ports["o2"])
    
    # Return Straight Path
    return_top = c << gf.components.straight(length=return_len, cross_section=xs)
    return_top.connect("o1", bend_top_right.ports["o2"])
    
    # Input Taper
    # Use cross_section to ensure correct layer inheritance
    taper = gf.components.taper(length=5.0, width1=width, width2=0.1, cross_section=xs)
    taper_top = c << taper
    taper_top.connect("o1", return_top.ports["o2"])
    
    # Flare out (Left side) - Curves UP and Away
    flare_top = c << gf.components.bend_euler(radius=bend_radius, angle=45, cross_section=xs)
    # Connect o1 to grating input. Mirroring forces the bend to curve "North" relative to West-facing port.
    flare_top.connect("o1", grating_top.ports["o1"], mirror=True)

    # --- 3. Bottom Assembly (Mirror Image) ---
    # Grating Section
    grating_bot = c << grating_waveguide(length=grating_len, width=width, layer=layer)
    grating_bot.move((0, -y_offset))
    
    # 180 degree U-Turn (Right side)
    bend_bot_right = c << gf.components.bend_euler(radius=bend_radius, angle=180, cross_section=xs)
    # Mirror the component vertically to bend downwards
    bend_bot_right.mirror()
    bend_bot_right.connect("o1", grating_bot.ports["o2"])
    
    # Return Straight Path
    return_bot = c << gf.components.straight(length=return_len, cross_section=xs)
    return_bot.connect("o1", bend_bot_right.ports["o2"])
    
    # Input Taper
    taper_bot = c << taper
    taper_bot.connect("o1", return_bot.ports["o2"])
    
    # Flare out (Left side) - Curves DOWN and Away
    flare_bot = c << gf.components.bend_euler(radius=bend_radius, angle=45, cross_section=xs)
    # Standard connection to West-facing port results in a "Left" (South) curve, which is correct for bottom.
    flare_bot.connect("o1", grating_bot.ports["o1"])

    return c

if __name__ == "__main__":
    device = photonic_cdc_device()
    device.write_gds("recreated_device.gds")
    device.show()