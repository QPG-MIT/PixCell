import gdsfactory as gf

@gf.cell
def recreate_directional_coupler():
    """
    Recreates the directional coupler from the image using parametric primitives.
    
    Footprint constraint: [120, 4]
    - Total Length: 120 um
    - Total Height: 4 um
    """
    c = gf.Component("directional_coupler")
    
    # --- Parameters ---
    # We define the geometry to fit exactly into 120x4 um
    wg_width = 0.5   # Standard waveguide width
    gap = 0.2        # Gap between waveguides in the coupling region
    
    # Length budget: 1/3 for input bends, 1/3 for coupler, 1/3 for output bends
    coupling_length = 40.0
    sbend_dx = 40.0
    
    # Height calculation:
    # center-to-center separation at coupling region = gap + wg_width = 0.7 um
    # desired center-to-center separation at ends = total_height - wg_width = 3.5 um
    # required vertical shift (dy) for each S-bend arm = (3.5 - 0.7) / 2 = 1.4 um
    sbend_dy = 1.4
    
    # --- Cross Section ---
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))
    
    # --- Primitives ---
    # Central coupling region
    # Ports: o1(bot-left), o2(top-left), o3(top-right), o4(bot-right)
    cp = gf.components.coupler_straight(length=coupling_length, gap=gap, cross_section=xs)
    
    # S-bend arms (Ports: o1, o2)
    sbend = gf.components.bend_s(size=(sbend_dx, sbend_dy), cross_section=xs)
    
    # --- Assembly ---
    # Add the central straight coupler
    cp_ref = c << cp
    
    # Left side arms
    # Connect right port (o2) of the S-bend to the left ports of the coupler
    sl_top = c << sbend
    sl_top.connect("o2", cp_ref.ports["o2"])
    
    sl_bot = c << sbend
    sl_bot.mirror_y() # Mirror to create the bottom flare
    sl_bot.connect("o2", cp_ref.ports["o1"])
    
    # Right side arms
    # Connect left port (o1) of the S-bend to the right ports of the coupler
    sr_top = c << sbend
    sr_top.connect("o1", cp_ref.ports["o3"])
    
    sr_bot = c << sbend
    sr_bot.mirror_y()
    sr_bot.connect("o1", cp_ref.ports["o4"])
    
    # --- External Ports ---
    c.add_port("o1", port=sl_bot.ports["o1"])
    c.add_port("o2", port=sl_top.ports["o1"])
    c.add_port("o3", port=sr_top.ports["o2"])
    c.add_port("o4", port=sr_bot.ports["o2"])
    
    return c

if __name__ == "__main__":
    # Create the component
    component = recreate_directional_coupler()
    
    # Access dimensions using xsize and ysize to avoid AttributeError
    print(f"Component dimensions: {component.xsize:.2f} um x {component.ysize:.2f} um")
    
    # Save the GDS file
    component.write_gds("directional_coupler.gds")
    
    # To view the result, you can use:
    # component.show()