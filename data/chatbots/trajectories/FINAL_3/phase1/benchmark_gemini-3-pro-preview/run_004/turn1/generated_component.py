import gdsfactory as gf

@gf.cell
def directional_coupler_4x240():
    """
    Recreates the directional coupler from the image based on the 
    4um x 240um footprint constraint.
    """
    c = gf.Component()

    # --- Geometric Parameters ---
    total_length = 240.0
    total_height = 4.0
    
    # Standard silicon photonics dimensions
    wg_width = 0.5
    gap = 0.2
    
    # Length partition (derived from visual aspect ratio)
    # The straight coupling region looks to be about 100um long
    coupling_length = 100.0
    bend_length = (total_length - coupling_length) / 2  # Result: 70um per bend

    # --- Vertical Offset Calculations ---
    # 1. Outer Ports (Inputs/Outputs):
    # To fit exactly inside 4um height, edges are at +2.0 and -2.0.
    # Center y = Edge - (Width/2)
    y_center_input = (total_height / 2) - (wg_width / 2) # 1.75 um

    # 2. Inner Ports (Coupling Region):
    # Center y = (Width + Gap) / 2
    y_center_coupling = (wg_width + gap) / 2 # 0.35 um

    # 3. The vertical shift (dy) required for the S-bends
    dy = y_center_input - y_center_coupling # 1.4 um

    # --- Define Cross Section ---
    xs = gf.cross_section.strip(width=wg_width)

    # --- 1. Create Central Coupling Region ---
    # We use coupler_straight to create the two parallel guides in the center
    # This automatically handles the gap.
    coupler_core = c << gf.components.coupler_straight(
        length=coupling_length, 
        gap=gap, 
        cross_section=xs
    )

    # --- 2. Create S-Bends ---
    # We define the shape based on (x_length, y_height)
    
    # Top Left Bend: Needs to drop down (-dy) to meet the coupler
    bend_in_top_ref = c << gf.components.bend_s(
        size=(bend_length, -dy), 
        cross_section=xs
    )
    
    # Bottom Left Bend: Needs to rise up (+dy) to meet the coupler
    bend_in_bot_ref = c << gf.components.bend_s(
        size=(bend_length, dy), 
        cross_section=xs
    )

    # Top Right Bend: Needs to rise up (+dy) leaving the coupler
    bend_out_top_ref = c << gf.components.bend_s(
        size=(bend_length, dy), 
        cross_section=xs
    )

    # Bottom Right Bend: Needs to drop down (-dy) leaving the coupler
    bend_out_bot_ref = c << gf.components.bend_s(
        size=(bend_length, -dy), 
        cross_section=xs
    )

    # --- 3. Assemble and Connect ---
    
    # Connect Inputs (Left side)
    # bend_s port 'o2' is the end of the bend. We connect that to the coupler inputs.
    # coupler_straight ports: o1 (top west), o2 (bot west), o3 (top east), o4 (bot east)
    
    bend_in_top_ref.connect("o2", coupler_core.ports["o1"])
    bend_in_bot_ref.connect("o2", coupler_core.ports["o2"])

    # Connect Outputs (Right side)
    # bend_s port 'o1' is the start of the bend. We connect that to coupler outputs.
    
    bend_out_top_ref.connect("o1", coupler_core.ports["o3"])
    bend_out_bot_ref.connect("o1", coupler_core.ports["o4"])

    # --- 4. Expose Ports ---
    c.add_port("o1", port=bend_in_top_ref.ports["o1"])
    c.add_port("o2", port=bend_in_bot_ref.ports["o1"])
    c.add_port("o3", port=bend_out_top_ref.ports["o2"])
    c.add_port("o4", port=bend_out_bot_ref.ports["o2"])

    return c

# Generate and Save
device = directional_coupler_4x240()
device.show() # View in KLayout/GDS viewer
device.write_gds("directional_coupler_recreated.gds")