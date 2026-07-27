import gdsfactory as gf

@gf.cell
def flared_waveguide(length=120, taper_len=20, width_narrow=0.5, width_wide=1.5):
    """Creates a single flared waveguide (Wide-Narrow-Wide)."""
    c = gf.Component()
    
    # Define segments
    t1 = c << gf.components.taper(length=taper_len, width1=width_wide, width2=width_narrow)
    s  = c << gf.components.straight(length=length - (2 * taper_len), width=width_narrow)
    t2 = c << gf.components.taper(length=taper_len, width1=width_narrow, width2=width_wide)
    
    # Connect
    s.connect("o1", t1.ports["o2"])
    t2.connect("o1", s.ports["o2"])
    
    # Add ports
    c.add_port("o1", port=t1.ports["o1"])
    c.add_port("o2", port=t2.ports["o2"])
    return c

@gf.cell
def device_layout():
    c = gf.Component()
    
    # Layout parameters
    pitch = 2.5
    y_offsets = [-2*pitch, -1*pitch, 0, 1*pitch, 2*pitch]
    
    # Assemble the 5 rows
    for i, y in enumerate(y_offsets):
        if i == 0 or i == 4:
            # Flared Waveguides (Top and Bottom)
            wg = c << flared_waveguide()
        elif i == 2:
            # Middle Bar (Thicker)
            wg = c << gf.components.straight(length=120, width=1.0)
        else:
            # Standard Straight (Inner)
            wg = c << gf.components.straight(length=120, width=0.5)
            
        wg.movey(y)
        
    return c

if __name__ == "__main__":
    # Create and write the GDS
    device = device_layout()
    device.write_gds("final_layout.gds")
    print("Device generated successfully as final_layout.gds")