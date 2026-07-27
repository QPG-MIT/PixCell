import gdsfactory as gf

@gf.cell
def star_petal_device() -> gf.Component:
    """
    Creates a symmetrical 4-petal star geometry using the intersection 
    of offset circles to create pointed 'lens' (vesica piscis) shapes, 
    matching the sharp tips seen in the reference image.
    """
    layer = (1, 0)
    footprint = 4.7
    
    # Parameters to create the pointed petal (lens) shape.
    # A radius of 3.0 offset by 2.4 produces a pointed lens of length 3.6 and width 1.2
    # This leaves exactly enough room for the straight cross tips to extend to 4.7
    radius = 3.0
    offset = 2.4
    tip_width = 0.15
    
    # 1. Base circle primitive
    circle_base = gf.components.circle(radius=radius, layer=layer)
    
    # 2. Create the Horizontal Pointed Lens (Intersection of top and bottom circles)
    c_up = gf.Component("circ_up")
    c_up.add_ref(circle_base).movey(offset)
    
    c_down = gf.Component("circ_down")
    c_down.add_ref(circle_base).movey(-offset)
    
    # "and" operation creates the sharp pointed overlapping region
    lens_h = gf.boolean(c_up, c_down, operation="and", layer=layer)
    
    # 3. Create the Vertical Pointed Lens (Intersection of left and right circles)
    c_right = gf.Component("circ_right")
    c_right.add_ref(circle_base).movex(offset)
    
    c_left = gf.Component("circ_left")
    c_left.add_ref(circle_base).movex(-offset)
    
    lens_v = gf.boolean(c_right, c_left, operation="and", layer=layer)
    
    # 4. Combine horizontal and vertical lenses into the central star
    star_core = gf.boolean(lens_h, lens_v, operation="or", layer=layer)
    
    # 5. Add the straight cross to enforce the exact 4.7 footprint 
    # and provide the flat rectangular ends
    cross = gf.components.cross(length=footprint, width=tip_width, layer=layer)
    
    # Final merge
    final_geom = gf.boolean(star_core, cross, operation="or", layer=layer)
    
    return final_geom


if __name__ == "__main__":
    # Create the component
    c = star_petal_device()
    
    # Explicitly write to GDS file
    c.write_gds("star_petal_device.gds")