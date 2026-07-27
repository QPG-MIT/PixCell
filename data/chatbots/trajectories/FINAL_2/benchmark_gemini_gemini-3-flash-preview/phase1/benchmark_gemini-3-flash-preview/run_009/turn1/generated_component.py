import gdsfactory as gf

@gf.cell
def recreate_device_silhouette():
    """
    Recreates the device geometry using parametric primitives.
    Total Footprint: 25um x 10um.
    """
    c = gf.Component("recreated_device")
    layer = (1, 0)
    
    # 1. Create the main rectangular body
    # We define it centered and move it so the bottom edge sits at y=0.
    body_width = 25.0
    body_height = 4.0
    rect = c << gf.components.rectangle(size=(body_width, body_height), layer=layer, centered=True)
    rect.movey(body_height / 2) # Bounds: x [-12.5, 12.5], y [0, 4]
    
    # 2. Define a single pillar component (taper + straight neck)
    # This allows us to reuse the geometry for the 4 pillars.
    pillar = gf.Component("pillar_unit")
    
    pillar_taper_h = 3.0
    pillar_neck_h = 2.0
    w_base = 2.5
    w_neck = 0.8
    
    # Tapered base section
    taper_part = pillar << gf.components.taper(
        length=pillar_taper_h, 
        width1=w_base, 
        width2=w_neck, 
        layer=layer
    )
    taper_part.rotate(90) # Orient vertically
    
    # Straight neck section
    neck_xs = gf.cross_section.cross_section(width=w_neck, layer=layer)
    neck_part = pillar << gf.components.straight(length=pillar_neck_h, cross_section=neck_xs)
    neck_part.rotate(90)
    # Connect the neck to the narrow end (o2) of the taper
    neck_part.connect("o1", taper_part.ports["o2"])
    
    # 3. Add four pillars to the top edge of the body (at y=4)
    # Spread them symmetrically across the 25um width
    pillar_x_coords = [-9.0, -3.0, 3.0, 9.0]
    for x in pillar_x_coords:
        p_ref = c << pillar
        p_ref.move((x, body_height))
        
    # 4. Add the bottom central taper (tip)
    # Points downward from the center of the bottom edge (y=0)
    tip_h = 1.0
    bottom_tip = c << gf.components.taper(
        length=tip_h, 
        width1=2.0, 
        width2=0.6, 
        layer=layer
    )
    bottom_tip.rotate(-90)
    bottom_tip.movey(0) # Port o1 is at the wide base, touching the body
    
    return c

if __name__ == "__main__":
    # Generate the component
    my_device = recreate_device_silhouette()
    
    # Save the result to a GDS file
    my_device.write_gds("device_recreation.gds")
    
    # Visualize the component
    my_device.show()