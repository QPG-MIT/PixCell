import gdsfactory as gf

@gf.cell
def create_s_shaped_grating_device():
    c = gf.Component()
    
    # Create a cross-section with a reasonable minimum radius
    xs = gf.cross_section.cross_section(
        width=0.5, 
        layer=(1, 0),
        radius=5.0,  # Set radius to 5.0
        radius_min=3.0  # Set minimum radius to 3.0
    )
    
    # Create central straight section
    central_length = 12.0  # Leave more space for larger bends
    central_wg = c << gf.components.straight(length=central_length, cross_section=xs)
    
    # Create gratings along the central waveguide
    tooth_width = 0.1
    tooth_height = 0.3
    tooth_spacing = 0.2
    num_teeth = int(central_length / (tooth_width + tooth_spacing)) - 2
    
    # Position teeth above and below the central waveguide
    for i in range(num_teeth):
        tooth_x = central_wg.xmin + tooth_width/2 + i * (tooth_width + tooth_spacing)
        
        # Upper teeth
        upper_tooth = c << gf.components.rectangle(
            size=(tooth_width, tooth_height), 
            layer=(1, 0), 
            centered=False
        )
        upper_tooth.move((tooth_x, central_wg.ymin - tooth_height/2))
        
        # Lower teeth
        lower_tooth = c << gf.components.rectangle(
            size=(tooth_width, tooth_height), 
            layer=(1, 0), 
            centered=False
        )
        lower_tooth.move((tooth_x, central_wg.ymax + tooth_height/2))
    
    # Create top curved arm using S-bend with larger size to ensure min radius constraint
    top_s_bend = c << gf.components.bend_s(
        size=(6.0, 3.0),  # Larger size to ensure bend radius >= 3.0
        cross_section=xs
    )
    top_s_bend.move((central_wg.xmin - 3.0, central_wg.ymin + 1.5))
    
    # Create bottom curved arm
    bottom_s_bend = c << gf.components.bend_s(
        size=(6.0, 3.0),  # Larger size to ensure bend radius >= 3.0
        cross_section=xs
    )
    bottom_s_bend.move((central_wg.xmin - 3.0, central_wg.ymax - 4.5))
    bottom_s_bend.rotate(180)
    
    # Add tapers to ends
    taper_length = 2.0
    top_taper = c << gf.components.taper(
        length=taper_length, 
        width1=0.5, 
        width2=0.1
    )
    top_taper.move((top_s_bend.xmin - taper_length, top_s_bend.ymin))
    top_taper.rotate(180)
    
    bottom_taper = c << gf.components.taper(
        length=taper_length, 
        width1=0.5, 
        width2=0.1
    )
    bottom_taper.move((bottom_s_bend.xmin - taper_length, bottom_s_bend.ymax))
    
    return c

# Create and save the device
device = create_s_shaped_grating_device()
device.write_gds("s_shaped_grating_device.gds")