import gdsfactory as gf

@gf.cell
def raceway_mzi_structure():
    # Main component to return
    c = gf.Component("raceway_mzi")
    layer = (1, 0)

    # ---------------------------------------------------------
    # 1. Additive Geometry (Outer Ring + Solid Inner Arms)
    # ---------------------------------------------------------
    c_add = gf.Component("additive_structures")

    # A) Outer Racetrack Ring
    # Footprint constraint is [3.0, 5.5] (Height x Width)
    # Racetrack width 5.5 = 2.5 (straight) + 2 * 1.5 (outer radius)
    # Racetrack height 3.0 = 2 * 1.5 (outer radius)
    xs_ring = gf.cross_section.cross_section(width=0.4, layer=layer)
    
    p_ring = gf.Path()
    p_ring.append(gf.path.straight(length=2.5))
    p_ring.append(gf.path.arc(radius=1.3, angle=180)) # 1.3 rad + 0.2 half-width = 1.5 outer bounds
    p_ring.append(gf.path.straight(length=2.5))
    p_ring.append(gf.path.arc(radius=1.3, angle=180))
    
    # Add ring and center it at (0,0) by moving the reference
    ref_ring = c_add << gf.path.extrude(p_ring, cross_section=xs_ring)
    ref_ring.move((-1.25, -1.3)) 

    # B) Inner Waveguide Tapers
    xs_arm = gf.cross_section.cross_section(width=0.2, layer=layer)

    # Path lines connecting the inner bounds of the ring to the horizontal phase shifters
    p_top_left = gf.Path([(-2.5, 0), (-1.2, 0.65)])
    c_add << gf.path.extrude(p_top_left, cross_section=xs_arm)

    p_top_right = gf.Path([(1.2, 0.65), (2.5, 0)])
    c_add << gf.path.extrude(p_top_right, cross_section=xs_arm)

    p_bot_left = gf.Path([(-2.5, 0), (-1.2, -0.65)])
    c_add << gf.path.extrude(p_bot_left, cross_section=xs_arm)

    p_bot_right = gf.Path([(1.2, -0.65), (2.5, 0)])
    c_add << gf.path.extrude(p_bot_right, cross_section=xs_arm)

    # C) Thick Horizontal Boxes (Where holes will be cut out)
    rect_box = gf.components.rectangle(size=(2.4, 0.6), centered=True, layer=layer)
    
    ref_box_top = c_add << rect_box
    ref_box_top.move((0, 0.65))
    
    ref_box_bot = c_add << rect_box
    ref_box_bot.move((0, -0.65))


    # ---------------------------------------------------------
    # 2. Subtractive Geometry (Rectangular Windows)
    # ---------------------------------------------------------
    c_sub = gf.Component("subtractive_structures")
    
    # Define the holes to be cut out of the boxes (leaving 0.1 border & 0.2 middle gap)
    rect_hole = gf.components.rectangle(size=(1.0, 0.4), centered=True, layer=layer)
    
    # Top arm windows
    ref_h1 = c_sub << rect_hole
    ref_h1.move((-0.6, 0.65))
    
    ref_h2 = c_sub << rect_hole
    ref_h2.move((0.6, 0.65))
    
    # Bottom arm windows
    ref_h3 = c_sub << rect_hole
    ref_h3.move((-0.6, -0.65))
    
    ref_h4 = c_sub << rect_hole
    ref_h4.move((0.6, -0.65))


    # ---------------------------------------------------------
    # 3. Final Boolean Composition
    # ---------------------------------------------------------
    # Carve the windows out of the solid inner shapes
    final_device = gf.boolean(c_add, c_sub, operation="not", layer=layer)
    
    c << final_device
    return c

if __name__ == "__main__":
    # Instantiate the component
    c = raceway_mzi_structure()
    
    # Write the required GDS file to disk
    c.write_gds("raceway_mzi.gds")