import gdsfactory as gf

@gf.cell
def directional_coupler_240x4():
    """
    Recreation of the directional coupler device based on image analysis
    and specific footprint constraints (4um x 240um).
    """
    c = gf.Component()
    
    # 1. Define Cross Section (Standard Silicon Photonics width)
    # Using layer (1,0) as per catalog examples
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))

    # 2. Define Dimensions based on Footprint Constraint
    total_length = 240.0
    total_height = 4.0
    
    # Internal geometry parameters
    coupling_length = 40.0  # Length of the parallel interaction region
    gap = 0.2               # Gap between waveguides in the center
    wg_width = 0.5
    
    # Calculate S-bend dimensions
    # Length of one s-bend = (Total Length - Coupling Length) / 2 sides
    bend_length = (total_length - coupling_length) / 2
    
    # Calculate Y-offsets (dy)
    # Inner separation (center-to-center) at the coupling region
    y_sep_inner = gap + wg_width
    
    # Outer separation (center-to-center) at the ports
    # We assume the 4um footprint is the outer edge to outer edge distance.
    # Therefore, center-to-center height = Total Height - Waveguide Width
    y_sep_outer = total_height - wg_width
    
    # The vertical shift (dy) required for the S-bend
    bend_dy = (y_sep_outer - y_sep_inner) / 2

    # 3. Create Primitives
    
    # Central Coupling Region
    # Catalog Function: gf.components.coupler_straight
    coupler = c << gf.components.coupler_straight(
        length=coupling_length, 
        gap=gap, 
        cross_section=xs
    )

    # S-Bend Generator
    # Catalog Function: gf.components.bend_s
    # Note: bend_s creates a bend from (0,0) to (x, y). 
    s_bend = gf.components.bend_s(
        size=(bend_length, bend_dy), 
        cross_section=xs
    )

    # 4. Assemble and Route (Left Side - Inputs)
    
    # Top Left Input
    # We connect the END of the S-bend (o2) to the coupler input (o1)
    # Because bend_s connects (0,0) to (L, h), connecting o2 (the 'high' side)
    # to the coupler matches the geometry.
    bl_top = c << s_bend
    bl_top.connect("o2", coupler.ports["o1"])

    # Bottom Left Input
    # We mirror the bend vertically to go 'down' into the coupler
    bl_bot = c << s_bend
    bl_bot.mirror() 
    bl_bot.connect("o2", coupler.ports["o2"])

    # 5. Assemble and Route (Right Side - Outputs)
    
    # Top Right Output
    # We connect the START of the S-bend (o1) to the coupler output (o3)
    br_top = c << s_bend
    br_top.connect("o1", coupler.ports["o3"])
    
    # Bottom Right Output
    # Mirror vertical again for the bottom path
    br_bot = c << s_bend
    br_bot.mirror()
    br_bot.connect("o1", coupler.ports["o4"])

    # 6. Expose Ports
    c.add_port("o1", port=bl_top.ports["o1"]) # Input Top
    c.add_port("o2", port=bl_bot.ports["o1"]) # Input Bottom
    c.add_port("o3", port=br_top.ports["o2"]) # Output Top
    c.add_port("o4", port=br_bot.ports["o2"]) # Output Bottom

    return c

if __name__ == "__main__":
    # Create the device
    device = directional_coupler_240x4()
    
    # Verify the footprint matches the request
    print(f"Device Size: {device.size_info.width} x {device.size_info.height}")
    
    # Show the device
    device.show()
    
    # Save GDS
    device.write_gds("coupler_recreation.gds")