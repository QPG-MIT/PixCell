import gdsfactory as gf

@gf.cell
def create_s_shaped_grating_device():
    c = gf.Component()
    
    # Create a cross-section with appropriate minimum radius
    xs = gf.cross_section.cross_section(
        width=0.5, 
        layer=(1, 0),
        radius=5.0,
        radius_min=3.0
    )
    
    # Create central straight section
    central_length = 14.0
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
    
    # Create top curved arm using path with smooth bends
    top_path = gf.Path()
    top_path.append(gf.path.straight(length=2.0))
    top_path.append(gf.path.euler(radius=4.0, angle=90))
    top_path.append(gf.path.straight(length=6.0))
    top_path.append(gf.path.euler(radius=4.0, angle=90))
    top_path.append(gf.path.straight(length=2.0))
    
    top_arm = c << gf.path.extrude(top_path, cross_section=xs)
    top_arm.move((central_wg.xmin - 2.0, central_wg.ymin + 0.5))
    top_arm.rotate(90)
    
    # Create bottom curved arm
    bottom_path = gf.Path()
    bottom_path.append(gf.path.straight(length=2.0))
    bottom_path.append(gf.path.euler(radius=4.0, angle=90))
    bottom_path.append(gf.path.straight(length=6.0))
    bottom_path.append(gf.path.euler(radius=4.0, angle=90))
    bottom_path.append(gf.path.straight(length=2.0))
    
    bottom_arm = c << gf.path.extrude(bottom_path, cross_section=xs)
    bottom_arm.move((central_wg.xmin - 2.0, central_wg.ymax - 0.5))
    bottom_arm.rotate(-90)
    
    # Add tapers to ends
    taper_length = 2.0
    top_taper = c << gf.components.taper(
        length=taper_length, 
        width1=0.5, 
        width2=0.1
    )
    top_taper.move((top_arm.xmax, top_arm.ymin))
    top_taper.rotate(90)
    
    bottom_taper = c << gf.components.taper(
        length=taper_length, 
        width1=0.5, 
        width2=0.1
    )
    bottom_taper.move((bottom_arm.xmax, bottom_arm.ymax))
    bottom_taper.rotate(-90)
    
    return c

# Create and save the device
device = create_s_shaped_grating_device()
device.write_gds("s_shaped_grating_device.gds")