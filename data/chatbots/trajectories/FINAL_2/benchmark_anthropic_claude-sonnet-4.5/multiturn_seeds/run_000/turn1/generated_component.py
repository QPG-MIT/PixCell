import gdsfactory as gf

@gf.cell
def create_pillar():
    """Create a single pillar structure with narrow neck"""
    c = gf.Component()
    
    # Top rectangular section
    top_width = 1.5
    top_height = 1.2
    top = c << gf.components.rectangle(
        size=(top_width, top_height),
        layer=(1, 0),
        centered=True
    )
    top.movey(1.9)
    
    # Middle narrow section (neck)
    neck_width = 1.2
    neck_height = 1.0
    neck = c << gf.components.rectangle(
        size=(neck_width, neck_height),
        layer=(1, 0),
        centered=True
    )
    neck.movey(0.8)
    
    # Bottom taper connecting to main body
    bottom_width = 2.0
    taper_height = 0.8
    taper = c << gf.components.taper(
        length=taper_height,
        width1=neck_width,
        width2=bottom_width,
        layer=(1, 0)
    )
    taper.rotate(90)
    taper.movey(0.0)
    
    return c

@gf.cell
def create_device():
    """Main device assembly"""
    c = gf.Component()
    
    # Main rectangular body dimensions (fits within 25x10 um footprint)
    main_width = 24.0
    main_height = 5.5
    
    # Create main rectangle centered at origin
    main_body = c << gf.components.rectangle(
        size=(main_width, main_height),
        layer=(1, 0),
        centered=True
    )
    
    # Add four pillars on top, evenly spaced
    num_pillars = 4
    pillar_spacing = main_width / (num_pillars + 1)
    
    for i in range(num_pillars):
        x_pos = -main_width/2 + pillar_spacing * (i + 1)
        pillar = c << create_pillar()
        pillar.move((x_pos, main_height/2))
    
    # Bottom triangular protrusion (pointing downward)
    triangle_width = 2.5
    triangle_height = 1.2
    triangle = c << gf.components.triangle(
        x=triangle_width,
        y=triangle_height,
        layer=(1, 0)
    )
    # Rotate 180 degrees to point downward
    triangle.rotate(180)
    triangle.movex(triangle_width/3)  # Center adjustment
    triangle.movey(-main_height/2 - triangle_height)
    
    return c

if __name__ == "__main__":
    # Create the device
    device = create_device()
    
    # Save to GDS file
    device.write_gds("device.gds")
    
    # Optional: show the device (if running in appropriate environment)
    # device.show()
    
    print("Device created successfully!")
    print(f"Bounding box: {device.bbox}")