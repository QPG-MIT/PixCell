import gdsfactory as gf

@gf.cell
def directional_coupler_240():
    """
    Recreates the directional coupler from the image based on the 
    4um x 240um footprint constraint.
    """
    c = gf.Component()

    # --- Parameters ---
    total_length = 240.0
    total_height = 4.0
    
    wg_width = 0.5
    gap = 0.2
    
    # Length of the central coupling region
    l_coupling = 100.0
    # Length of the straight input/output sections
    l_io = 10.0
    
    # --- Derived Geometry ---
    # Calculate vertical centers to match the 4um total height
    # Top edge = +2.0, Center = +1.75
    y_center_outer = (total_height / 2) - (wg_width / 2)
    # Inner gap center for coupling = +0.35
    y_center_inner = (gap / 2) + (wg_width / 2)
    
    # Vertical displacement for the S-bend
    dy = y_center_outer - y_center_inner
    
    # Calculate S-bend length to fill remaining space
    # Total = 2*l_io + 2*l_sbend + l_coupling
    l_sbend = (total_length - l_coupling - (2 * l_io)) / 2

    # Define Cross Section
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))

    # --- Component Definition ---

    # 1. Central Coupler (Two parallel straights)
    coupler = c << gf.components.coupler_straight(
        length=l_coupling, 
        gap=gap, 
        cross_section=xs
    )

    # 2. S-Bend Definition
    # Defined once, used 4 times
    s_bend_ref = gf.components.bend_s(
        size=(l_sbend, dy), 
        cross_section=xs
    )

    # 3. IO Straight Definition
    straight_ref = gf.components.straight(
        length=l_io, 
        cross_section=xs
    )

    # --- Assembly & Connections ---

    # -- Left Side (Inputs) --
    
    # Top Left S-Bend
    sb_tl = c << s_bend_ref
    # Connect the "wide" end (o2) of the s-bend to the "narrow" input (o1) of the coupler
    # Because bend_s usually goes UP, and we are connecting to the top port, 
    # we connect the END of the bend to the START of the coupler.
    sb_tl.connect("o2", coupler.ports["o1"])
    
    # Bottom Left S-Bend
    sb_bl = c << s_bend_ref
    # For the bottom, the bend goes UP from -y_outer to -y_inner.
    # The standard bend_s shape fits this perfectly if we connect the end (o2) to the coupler.
    sb_bl.connect("o2", coupler.ports["o2"])

    # Top Left Straight Input
    wg_tl = c << straight_ref
    wg_tl.connect("o2", sb_tl.ports["o1"])

    # Bottom Left Straight Input
    wg_bl = c << straight_ref
    wg_bl.connect("o2", sb_bl.ports["o1"])


    # -- Right Side (Outputs) --

    # Top Right S-Bend
    sb_tr = c << s_bend_ref
    # Here we connect the START (o1) of the bend to the END (o3) of the coupler.
    sb_tr.connect("o1", coupler.ports["o3"])

    # Bottom Right S-Bend
    sb_br = c << s_bend_ref
    # The standard bend goes UP. We need to go DOWN from the coupler to the output.
    # We mirror the bend vertically.
    sb_br.mirror_y() 
    sb_br.connect("o1", coupler.ports["o4"])

    # Top Right Straight Output
    wg_tr = c << straight_ref
    wg_tr.connect("o1", sb_tr.ports["o2"])

    # Bottom Right Straight Output
    wg_br = c << straight_ref
    wg_br.connect("o1", sb_br.ports["o2"])


    # --- Expose Ports ---
    c.add_port("o1", port=wg_tl.ports["o1"]) # Top Left
    c.add_port("o2", port=wg_bl.ports["o1"]) # Bottom Left
    c.add_port("o3", port=wg_tr.ports["o2"]) # Top Right
    c.add_port("o4", port=wg_br.ports["o2"]) # Bottom Right

    return c

# Generate and Show
device = directional_coupler_240()
device.show() # Opens in KLayout if installed, or creates GDS
device.write_gds("directional_coupler_240.gds")