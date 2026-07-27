import gdsfactory as gf

@gf.cell
def recreate_device():
    """
    Recreates the waveguide coupler geometry from the image.
    
    Geometry:
    - Central straight waveguide that terminates early.
    - Symmetric outer waveguides that start straight and transition outwards.
    
    Footprint constraint: [40.0, 1.7] um
    """
    c = gf.Component("waveguide_coupler")

    # --- Design Parameters ---
    total_length = 40.0
    total_height = 1.7
    wg_width = 0.3
    
    # Target height is 1.7um. 
    # Center-to-center final offset = (Total Height / 2) - (Width / 2)
    # y_final = (1.7 / 2) - (0.3 / 2) = 0.7 um
    y_final = 0.7
    y_initial = 0.4  # Initial gap spacing
    dy = y_final - y_initial
    
    # Longitudinal split: Straight section then S-Bend
    l_straight = 22.0
    l_sbend = total_length - l_straight
    l_center = 25.0  # Center waveguide terminates slightly after the bend starts
    
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))

    # --- 1. Central Waveguide ---
    center_wg = c << gf.components.straight(length=l_center, cross_section=xs)
    center_wg.movey(0)

    # --- 2. Top Arm ---
    top_str = c << gf.components.straight(length=l_straight, cross_section=xs)
    top_str.movey(y_initial)
    
    # Connect an S-bend to the end of the straight segment
    top_bend = c << gf.components.bend_s(size=(l_sbend, dy), cross_section=xs)
    top_bend.connect("o1", top_str.ports["o2"])

    # --- 3. Bottom Arm ---
    bot_str = c << gf.components.straight(length=l_straight, cross_section=xs)
    bot_str.movey(-y_initial)
    
    # Connect a mirrored S-bend to the end of the straight segment
    bot_bend = c << gf.components.bend_s(size=(l_sbend, -dy), cross_section=xs)
    bot_bend.connect("o1", bot_str.ports["o2"])

    # --- Port Mapping ---
    c.add_port("o1", port=center_wg.ports["o1"])
    c.add_port("o2", port=top_str.ports["o1"])
    c.add_port("o3", port=bot_str.ports["o1"])
    c.add_port("o4", port=top_bend.ports["o2"])
    c.add_port("o5", port=bot_bend.ports["o2"])

    return c

if __name__ == "__main__":
    # Create the component
    component = recreate_device()
    
    # Verify dimensions
    print(f"Final footprint: {component.xsize:.2f} x {component.ysize:.2f} um")
    
    # Write the GDS file to the current directory
    filename = "recreated_device.gds"
    component.write_gds(filename)
    print(f"GDS file saved as: {filename}")
    
    # Optional: Open in viewer if configured
    # component.show()