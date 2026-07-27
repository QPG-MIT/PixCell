import gdsfactory as gf

@gf.cell
def spot_size_converter():
    """
    Creates a GDSFactory component that replicates the device shown in the image.
    The device is a mode converter or adiabatic coupler consisting of:
    1. A central waveguide that starts straight and then tapers to a point.
    2. Two outer waveguides that follow the central taper, widening as they go, 
       and then curving outwards in an S-bend.

    The total footprint is constrained to 40.0 um x 1.7 um.
    """
    c = gf.Component()
    layer = (1, 0)

    # Dimensional parameters based on footprint and image analysis
    L_total = 40.0
    L_start_straight = 3.2   # Length of the central straight section before side waveguides appear
    L_central_taper = 22.8   # Length of the central taper section
    L_final_section = 14.0   # Length of the remaining S-bend section (Total = 3.2 + 22.8 + 14.0 = 40.0)

    # 1. Central Waveguide
    # Starts from the far left (x=0)
    # width approx 0.28 um (scaled from pixel measurements)
    w_c_start = 0.28
    w_c_end = 0.02  # Tapering to a narrow tip

    # Straight segment at the start
    c_straight = c << gf.components.straight(length=L_start_straight, width=w_c_start, layer=layer)
    c_straight.movex(0)
    
    # Tapering segment that ends where the side waveguides begin their curves
    c_taper = c << gf.components.taper(length=L_central_taper, width1=w_c_start, width2=w_c_end, layer=layer)
    c_taper.connect("o1", c_straight.ports["o2"])

    # 2. Side Waveguides (Top and Bottom)
    # They start at the same x-position where the central waveguide begins to taper
    # width starts narrow (~0.07 um) and widens (~0.24 um)
    w_s_start = 0.07
    w_s_end = 0.24
    
    # Gap between central and side waveguides at start
    gap_init = 0.10
    # y-coordinate for the center of the side waveguides at the start
    y0 = w_c_start / 2 + gap_init + w_s_start / 2  # ~0.14 + 0.10 + 0.035 = 0.275 um
    
    # Final y-coordinate at the right end for the center of the side waveguides
    # Calculated so the outer edge is at 0.85 um (half of 1.7 um total height)
    yf = 0.85 - w_s_end / 2 # ~0.85 - 0.12 = 0.73 um

    # --- Top Side Waveguide ---
    # Straight taper following the central waveguide
    side_taper_top = c << gf.components.taper(length=L_central_taper, width1=w_s_start, width2=w_s_end, layer=layer)
    side_taper_top.move((L_start_straight, y0))
    
    # S-bend connecting to the output
    side_sbend_top = c << gf.components.bend_s(
        size=(L_final_section, yf - y0), 
        cross_section=gf.cross_section.cross_section(width=w_s_end, layer=layer)
    )
    side_sbend_top.connect("o1", side_taper_top.ports["o2"])

    # --- Bottom Side Waveguide ---
    # Symmetric to the top waveguide
    side_taper_bot = c << gf.components.taper(length=L_central_taper, width1=w_s_start, width2=w_s_end, layer=layer)
    side_taper_bot.move((L_start_straight, -y0))
    
    side_sbend_bot = c << gf.components.bend_s(
        size=(L_final_section, -(yf - y0)), 
        cross_section=gf.cross_section.cross_section(width=w_s_end, layer=layer)
    )
    side_sbend_bot.connect("o1", side_taper_bot.ports["o2"])

    return c

if __name__ == "__main__":
    # Create the component
    device = spot_size_converter()
    
    # Save the GDS file
    device.write_gds("device.gds")
