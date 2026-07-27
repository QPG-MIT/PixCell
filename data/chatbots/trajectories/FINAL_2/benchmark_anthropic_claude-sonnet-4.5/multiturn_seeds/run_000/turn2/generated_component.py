import gdsfactory as gf

@gf.cell
def create_arrow_pillar():
    """Create a single arrow-shaped pillar pointing downward"""
    c = gf.Component()
    
    # Top narrow shaft (the arrow shaft)
    shaft_width = 1.8
    shaft_height = 4.0
    shaft = c << gf.components.rectangle(
        size=(shaft_width, shaft_height),
        layer=(1, 0),
        centered=True
    )
    shaft.movey(shaft_height/2)
    
    # Middle wider section
    middle_width = 2.2
    middle_height = 1.0
    middle = c << gf.components.rectangle(
        size=(middle_width, middle_height),
        layer=(1, 0),
        centered=True
    )
    middle.movey(-middle_height/2)
    
    # Arrow head (trapezoid shape pointing down)
    # Create using a polygon for better control
    arrow_height = 2.5
    arrow_top_width = 2.2
    arrow_bottom_width = 4.0
    
    points = [
        (-arrow_top_width/2, 0),
        (arrow_top_width/2, 0),
        (arrow_bottom_width/2, -arrow_height),
        (-arrow_bottom_width/2, -arrow_height),
    ]
    
    arrow = c.add_polygon(points, layer=(1, 0))
    
    return c

@gf.cell
def create_device():
    """Main device assembly"""
    c = gf.Component()
    
    # Main rectangular body dimensions
    main_width = 30.0
    main_height = 8.0
    
    # Create main rectangle
    main_body = c << gf.components.rectangle(
        size=(main_width, main_height),
        layer=(1, 0),
        centered=True
    )
    main_body.movey(-2.0)  # Position lower
    
    # Add four arrow pillars on top, evenly spaced
    num_pillars = 4
    # Calculate spacing to evenly distribute pillars
    usable_width = main_width - 4.0  # Leave margins
    pillar_spacing = usable_width / (num_pillars - 1)
    start_x = -usable_width / 2
    
    for i in range(num_pillars):
        x_pos = start_x + pillar_spacing * i
        pillar = c << create_arrow_pillar()
        pillar.move((x_pos, main_height/2 - 2.0))
    
    # Bottom triangular protrusion (pointing downward)
    triangle_width = 3.0
    triangle_height = 2.0
    
    # Create triangle pointing down
    triangle_points = [
        (0, -main_height/2 - 2.0),
        (-triangle_width/2, -main_height/2 - 2.0 - triangle_height),
        (triangle_width/2, -main_height/2 - 2.0 - triangle_height),
    ]
    
    c.add_polygon(triangle_points, layer=(1, 0))
    
    return c

if __name__ == "__main__":
    # Create the device
    device = create_device()
    
    # Save to GDS file
    device.write_gds("device.gds")
    
    print("Device created successfully!")
    print(f"Bounding box: {device.bbox}")