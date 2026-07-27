import gdsfactory as gf

@gf.cell
def device_mmi_1x4():
    """
    Parametric recreation of the 1x4 MMI device.
    Generates a GDS file matching the visual topology and 25x10um footprint.
    """
    c = gf.Component()

    # =======================================================================
    # Parameters
    # =======================================================================
    # Footprint constraint: 25um x 10um
    
    # Main Body Dimensions
    mmi_width = 12.0
    mmi_length = 5.0
    
    # Port Geometry
    # Top ports: Taper + Straight extension
    top_taper_len = 2.0
    top_straight_len = 0.5 
    
    # Bottom port: Short taper
    bot_taper_len = 1.5
    
    # Widths
    width_mmi_interface = 1.8  # Wide end of taper
    width_waveguide = 0.6      # Narrow end of taper (waveguide mode)
    
    # Array Spacing
    port_pitch = 2.5
    
    # Layer Definition
    layer_device = (1, 0)
    
    # Define Cross Section (required for waveguide primitives)
    xs = gf.cross_section.cross_section(width=width_waveguide, layer=layer_device)

    # =======================================================================
    # 1. Main MMI Body
    # =======================================================================
    # Central rectangle
    mmi = c << gf.components.rectangle(
        size=(mmi_width, mmi_length), 
        layer=layer_device, 
        centered=True
    )

    # =======================================================================
    # 2. Top Output Ports (Array of 4)
    # =======================================================================
    # Define primitives
    # Taper: transitions from MMI width to waveguide width
    t_top_cmp = gf.components.taper(
        length=top_taper_len,
        width1=width_mmi_interface,
        width2=width_waveguide,
        cross_section=xs
    )
    
    # Straight: extension for the ports
    s_top_cmp = gf.components.straight(
        length=top_straight_len,
        cross_section=xs
    )
    
    # Calculate positions
    n_ports = 4
    # Center the array around x=0
    x_start = -(n_ports - 1) * port_pitch / 2.0
    y_top_edge = mmi_length / 2.0
    
    for i in range(n_ports):
        x_pos = x_start + i * port_pitch
        
        # Add Taper
        ref_t = c << t_top_cmp
        ref_t.rotate(90)
        ref_t.x = x_pos
        ref_t.ymin = y_top_edge
        
        # Add Straight Extension
        ref_s = c << s_top_cmp
        ref_s.rotate(90)
        ref_s.x = x_pos
        ref_s.ymin = ref_t.ymax

    # =======================================================================
    # 3. Bottom Input Port (Single)
    # =======================================================================
    # Define primitive (shorter taper)
    t_bot_cmp = gf.components.taper(
        length=bot_taper_len,
        width1=width_mmi_interface,
        width2=width_waveguide,
        cross_section=xs
    )
    
    y_bot_edge = -mmi_length / 2.0
    
    # Add Taper
    ref_b = c << t_bot_cmp
    ref_b.rotate(-90)
    ref_b.x = 0
    ref_b.ymax = y_bot_edge

    return c

if __name__ == "__main__":
    # 1. Instantiate the device
    device = device_mmi_1x4()
    
    # 2. Write the GDS file to disk
    device.write_gds("mmi_1x4.gds")
    
    # 3. Print confirmation and stats
    print(f"Successfully wrote mmi_1x4.gds")
    print(f"Device Name: {device.name}")
    print(f"Device Size (um): {device.size}")