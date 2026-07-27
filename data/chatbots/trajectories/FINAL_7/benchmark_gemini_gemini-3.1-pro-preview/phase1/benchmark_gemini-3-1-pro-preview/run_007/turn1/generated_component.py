import gdsfactory as gf

@gf.cell
def device():
    # Main container
    c = gf.Component()
    layer = (1, 0)

    # ---------------------------------------------------------
    # 1. Create the Racetrack Ring (Outer solid minus Inner empty)
    # ---------------------------------------------------------
    
    # Outer pill shape (footprint 5.5 x 3.0)
    c_out = gf.Component("outer_pill")
    ref_out_rect = c_out << gf.components.rectangle(size=(2.5, 3.0), centered=True, layer=layer)
    ref_out_c1 = c_out << gf.components.circle(radius=1.5, layer=layer)
    ref_out_c1.move((-1.25, 0))
    ref_out_c2 = c_out << gf.components.circle(radius=1.5, layer=layer)
    ref_out_c2.move((1.25, 0))

    # Inner pill shape (to subtract)
    c_in = gf.Component("inner_pill")
    ref_in_rect = c_in << gf.components.rectangle(size=(2.5, 2.0), centered=True, layer=layer)
    ref_in_c1 = c_in << gf.components.circle(radius=1.0, layer=layer)
    ref_in_c1.move((-1.25, 0))
    ref_in_c2 = c_in << gf.components.circle(radius=1.0, layer=layer)
    ref_in_c2.move((1.25, 0))

    # Subtract to get the racetrack ring
    racetrack = gf.boolean(c_out, c_in, operation="not", layer=layer)

    # ---------------------------------------------------------
    # 2. Create the Central MZI Structures (Arms and solid boxes)
    # ---------------------------------------------------------
    
    c_center = gf.Component("center_solid")

    # The arms use a path extruded with a cross section
    xs = gf.cross_section.cross_section(width=0.2, layer=layer)
    
    # Paths slightly overlap into the inner ring bounds (x=±2.25) to ensure solid boolean union
    p_top = gf.Path([(-2.4, 0), (-1.6, 0), (-1.0, 0.4), (1.0, 0.4), (1.6, 0), (2.4, 0)])
    p_bot = gf.Path([(-2.4, 0), (-1.6, 0), (-1.0, -0.4), (1.0, -0.4), (1.6, 0), (2.4, 0)])

    c_center << gf.path.extrude(p_top, cross_section=xs)
    c_center << gf.path.extrude(p_bot, cross_section=xs)

    # Add the solid bounding boxes for the phase shifters / splitters
    ref_box_t = c_center << gf.components.rectangle(size=(1.5, 0.4), centered=True, layer=layer)
    ref_box_t.move((0, 0.4))
    
    ref_box_b = c_center << gf.components.rectangle(size=(1.5, 0.4), centered=True, layer=layer)
    ref_box_b.move((0, -0.4))

    # Union the racetrack ring and central solid structures
    c_solid = gf.boolean(racetrack, c_center, operation="or", layer=layer)

    # ---------------------------------------------------------
    # 3. Create the Holes for the Boxes
    # ---------------------------------------------------------
    
    c_holes = gf.Component("holes")
    
    # Top arm box holes
    ref_h1 = c_holes << gf.components.rectangle(size=(0.6, 0.2), centered=True, layer=layer)
    ref_h1.move((-0.35, 0.4))
    ref_h2 = c_holes << gf.components.rectangle(size=(0.6, 0.2), centered=True, layer=layer)
    ref_h2.move((0.35, 0.4))
    
    # Bottom arm box holes
    ref_h3 = c_holes << gf.components.rectangle(size=(0.6, 0.2), centered=True, layer=layer)
    ref_h3.move((-0.35, -0.4))
    ref_h4 = c_holes << gf.components.rectangle(size=(0.6, 0.2), centered=True, layer=layer)
    ref_h4.move((0.35, -0.4))

    # ---------------------------------------------------------
    # 4. Final Composition
    # ---------------------------------------------------------
    
    # Subtract the holes from the combined solid shape
    final_dev = gf.boolean(c_solid, c_holes, operation="not", layer=layer)
    
    c << final_dev
    return c

if __name__ == "__main__":
    # Ensure the GDS file is correctly written out
    c = device()
    c.write_gds("device.gds")