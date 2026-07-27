import gdsfactory as gf

@gf.cell
def mirrored_coupler(
    total_length: float = 120.0,
    total_height: float = 4.0,
    wg_width: float = 0.5,
    gap: float = 0.2,
    coupling_length: float = 40.0,
    s_bend_length: float = 30.0,
) -> gf.Component:
    """
    Recreates the directional coupler from the image using parametric primitives.
    
    Args:
        total_length: Total width of the device (120um).
        total_height: Total height of the device (4um).
        wg_width: Width of the waveguides.
        gap: Gap between waveguides in the coupling region.
        coupling_length: Length of the central straight coupling section.
        s_bend_length: Horizontal reach of the S-bends.
    """
    c = gf.Component("directional_coupler")
    
    # Define the cross section based on the catalog
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))
    
    # Calculate derived dimensions to fit the footprint
    # Total Length = 2*arm_length + 2*s_bend_length + coupling_length
    arm_length = (total_length - coupling_length - 2 * s_bend_length) / 2
    
    # Vertical centerlines for the footprint boundaries
    # The top of the top waveguide should be at total_height / 2
    y_outer = (total_height / 2) - (wg_width / 2)
    # The inner edge of the coupling waveguide should be at gap / 2
    y_inner = (gap / 2) + (wg_width / 2)
    
    # Vertical offset for the S-bend transition
    dy = y_inner - y_outer  # Negative value for the top branch converging down
    
    # --- 1. Create a single branch (top half) ---
    branch = gf.Component("coupler_branch")
    
    # Create segments
    left_arm = branch << gf.components.straight(length=arm_length, cross_section=xs)
    sb_in = branch << gf.components.bend_s(size=(s_bend_length, dy), cross_section=xs)
    middle = branch << gf.components.straight(length=coupling_length, cross_section=xs)
    sb_out = branch << gf.components.bend_s(size=(s_bend_length, -dy), cross_section=xs)
    right_arm = branch << gf.components.straight(length=arm_length, cross_section=xs)
    
    # Connect segments together sequentially
    sb_in.connect("o1", left_arm.ports["o2"])
    middle.connect("o1", sb_in.ports["o2"])
    sb_out.connect("o1", middle.ports["o2"])
    right_arm.connect("o1", sb_out.ports["o2"])
    
    # --- 2. Assemble the full device ---
    # Add top branch
    top = c << branch
    top.movey(y_outer)
    
    # Add bottom branch by mirroring the top branch
    bot = c << branch
    bot.mirror_y()
    bot.movey(-y_outer)
    
    return c

if __name__ == "__main__":
    # Create the component
    component = mirrored_coupler()
    
    # Export to GDS
    component.write_gds("recreated_coupler.gds")
    
    # Visual check (if environment supports it)
    component.show()