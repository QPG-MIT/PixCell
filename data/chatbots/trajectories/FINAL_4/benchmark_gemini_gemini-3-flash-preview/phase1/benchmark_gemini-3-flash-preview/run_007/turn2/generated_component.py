import gdsfactory as gf

@gf.cell
def create_curved_coupler():
    """
    Recreates the curved directional coupler from the image.
    Dimensions: 18um (Width) x 3um (Height)
    """
    # 1. Define physical constraints to hit the 18x3um footprint exactly
    target_width = 18.0
    target_height = 3.0
    wg_width = 0.6         # Visual proportion matching the image
    coupling_gap = 0.1     # Narrow gap for the 'waist'
    coupling_length = 2.0  # Length of the parallel central section
    
    # 2. Calculate S-bend dimensions
    # Horizontal length of each arm
    dx = (target_width - coupling_length) / 2.0
    
    # Vertical shift (dy) for the centers of the waveguides
    # Center y-coord at the coupler waist: (gap/2 + width/2)
    # Center y-coord at the end (to touch the 3um boundary): (target_height/2 - width/2)
    y_waist_center = (coupling_gap / 2.0) + (wg_width / 2.0)
    y_end_center = (target_height / 2.0) - (wg_width / 2.0)
    dy = y_end_center - y_waist_center
    
    # 3. Define Cross Section
    xs = gf.cross_section.strip(width=wg_width, layer=(1, 0))
    
    # 4. Create Component
    c = gf.Component("directional_coupler")
    
    # 5. Add the central parallel region
    # Ports: o1(tl), o2(bl), o3(tr), o4(br)
    center = c << gf.components.coupler_straight(
        length=coupling_length, 
        gap=coupling_gap, 
        cross_section=xs
    )
    
    # 6. Add and connect the S-bend arms
    # bend_s size is (dx, dy). dy sign determines direction.
    # Left arms connect to center o1/o2. Right arms connect to center o3/o4.
    
    # Left Side
    l_top = c << gf.components.bend_s(size=(dx, -dy), cross_section=xs)
    l_bot = c << gf.components.bend_s(size=(dx, dy), cross_section=xs)
    l_top.connect("o2", center.ports["o1"])
    l_bot.connect("o2", center.ports["o2"])
    
    # Right Side
    r_top = c << gf.components.bend_s(size=(dx, dy), cross_section=xs)
    r_bot = c << gf.components.bend_s(size=(dx, -dy), cross_section=xs)
    r_top.connect("o1", center.ports["o3"])
    r_bot.connect("o1", center.ports["o4"])
    
    # 7. Add external ports
    c.add_port("o1", port=l_top.ports["o1"])
    c.add_port("o2", port=l_bot.ports["o1"])
    c.add_port("o3", port=r_top.ports["o2"])
    c.add_port("o4", port=r_bot.ports["o2"])
    
    return c

if __name__ == "__main__":
    # Initialize the component
    component = create_curved_coupler()
    
    # Explicitly write the GDS file
    gds_filename = "curved_coupler.gds"
    component.write_gds(gds_filename)
    
    # Print verification info
    print(f"GDS file successfully saved as: {gds_filename}")
    
    # Dimension check (handles kfactory/GDSFactory version differences)
    try:
        bbox = component.dbbox()
        print(f"Footprint: {bbox.width():.2f}um x {bbox.height():.2f}um")
    except AttributeError:
        print(f"Footprint: {component.xsize:.2f}um x {component.ysize:.2f}um")