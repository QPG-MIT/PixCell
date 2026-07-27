import gdsfactory as gf

@gf.cell
def directional_coupler_240():
    """
    Directional coupler recreated using GDSFactory parametric primitives.
    Footprint constraint: 4 um x 240 um.
    """
    c = gf.Component()

    # --- Design Parameters ---
    total_length = 240.0
    # Vertical bounds are 4.0um. We set ports slightly inside this.
    port_separation = 3.0  
    
    # Waveguide Physics
    wg_width = 0.5
    coupling_gap = 0.2
    
    # Geometry calculations
    # Visually, the straight section is much longer than the bends.
    sbend_length = 40.0
    straight_length = total_length - (2 * sbend_length)
    
    # Calculate the vertical shift (dy) required for the S-bends
    # Distance from center axis to port
    y_port = port_separation / 2  
    # Distance from center axis to coupling waveguide
    y_couple = (coupling_gap + wg_width) / 2
    # The height the S-bend must traverse
    dy = y_port - y_couple

    # Define Cross Section (Standard Strip)
    xs = gf.cross_section.strip(width=wg_width)

    # --- 1. Create Coupling Region (Middle) ---
    # Using catalog function: gf.components.coupler_straight
    coupler = c << gf.components.coupler_straight(
        length=straight_length, 
        gap=coupling_gap, 
        cross_section=xs
    )

    # --- 2. Define S-Bend Component ---
    # Using catalog function: gf.components.bend_s
    # size = (length_x, height_y)
    bend_ref = gf.components.bend_s(
        size=(sbend_length, dy), 
        cross_section=xs
    )

    # --- 3. Assembly (Connecting components) ---
    
    # -- Left Side (Inputs) --
    
    # Top Left S-Bend
    # We mirror_y because bend_s typically goes 'up', we need it to go 'down' into the coupler
    tl = c << bend_ref
    tl.mirror_y()
    # Connect the END of the bend (narrow side) to the Top-West port of the coupler
    tl.connect("o2", coupler.ports["o1"])

    # Bottom Left S-Bend
    bl = c << bend_ref
    # Connect the END of the bend to the Bottom-West port of the coupler
    bl.connect("o2", coupler.ports["o2"])

    # -- Right Side (Outputs) --
    
    # Top Right S-Bend
    tr = c << bend_ref
    # Connect the START of the bend to the Top-East port of the coupler
    tr.connect("o1", coupler.ports["o3"])

    # Bottom Right S-Bend
    br = c << bend_ref
    br.mirror_y()
    # Connect the START of the bend to the Bottom-East port of the coupler
    br.connect("o1", coupler.ports["o4"])

    # --- 4. Expose Ports (Optional, for routing) ---
    c.add_port("o1", port=tl.ports["o1"]) # Top Input
    c.add_port("o2", port=bl.ports["o1"]) # Bot Input
    c.add_port("o3", port=tr.ports["o2"]) # Top Output
    c.add_port("o4", port=br.ports["o2"]) # Bot Output

    return c

# Generate and Save
device = directional_coupler_240()
device.write_gds("directional_coupler_240.gds")

# Visualization (if running in notebook/GUI)
device.show()