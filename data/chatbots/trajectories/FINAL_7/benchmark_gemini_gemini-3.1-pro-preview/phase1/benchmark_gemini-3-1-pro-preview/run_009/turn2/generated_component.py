import gdsfactory as gf

@gf.cell
def raceway_mzi_structure():
    # Main component
    c = gf.Component("raceway_mzi")
    layer = (1, 0)

    # ---------------------------------------------------------
    # 1. Additive Geometry (Outer Ring + Solid Inner Arms)
    # ---------------------------------------------------------
    c_add = gf.Component("additive_structures")

    # A) Outer Racetrack Ring
    # Footprint constraint: [3.0, 5.5] (Height x Width)
    # The path length is 2.5 + arc diameter 2.6 = 5.1 path width
    # Add line width 0.4 -> Total Width = 5.5
    # Arc diameter 2.6 + line width 0.4 -> Total Height = 3.0
    xs_ring = gf.cross_section.cross_section(width=0.4, layer=layer)
    
    p_ring = gf.Path()
    p_ring.append(gf.path.straight(length=2.5))
    p_ring.append(gf.path.arc(radius=1.3, angle=180)) 
    p_ring.append(gf.path.straight(length=2.5))
    p_ring.append(gf.path.arc(radius=1.3, angle=180))
    
    ref_ring = c_add << gf.path.extrude(p_ring, cross_section=xs_ring)
    ref_ring.move((-1.25, -1.3)) # Centers the whole ring at (0,0)

    # B) Inner Solid Arms (Drawn as thick continuous traces)
    # By making these continuous and thick, their central overlap forms a perfect solid stem.
    xs_arm = gf.cross_section.cross_section(width=0.45, layer=layer)

    # Top Arm Path: Stem -> Angle Up -> Straight -> Angle Down -> Stem
    pts_top = [
        (-2.45, 0),     # Embedded in the left inner arc
        (-1.5, 0),      # Left stem end / split start
        (-0.9, 0.55),   # Angled transition up to phase shifter
        (0.9, 0.55),    # Straight horizontal segment 
        (1.5, 0),       # Angled transition back down
        (2.45, 0)       # Embedded in the right inner arc
    ]
    c_add << gf.path.extrude(gf.Path(pts_top), cross_section=xs_arm)

    # Bottom Arm Path: Stem -> Angle Down -> Straight -> Angle Up -> Stem
    pts_bot = [
        (-2.45, 0),    
        (-1.5, 0),     
        (-0.9, -0.55),  
        (0.9, -0.55),   
        (1.5, 0),      
        (2.45, 0)      
    ]
    c_add << gf.path.extrude(gf.Path(pts_bot), cross_section=xs_arm)


    # ---------------------------------------------------------
    # 2. Subtractive Geometry (Rectangular Windows)
    # ---------------------------------------------------------
    c_sub = gf.Component("subtractive_structures")
    
    # We carve holes into the horizontal blocks to leave consistent 0.1um borders.
    # Total straight horizontal length is 1.8 (from X = -0.9 to 0.9)
    # Arm width is 0.45. Hole width 0.75 and height 0.25 fits perfectly.
    rect_hole = gf.components.rectangle(size=(0.75, 0.25), centered=True, layer=layer)
    
    # Top arm windows
    ref_h1 = c_sub << rect_hole
    ref_h1.move((-0.425, 0.55))
    
    ref_h2 = c_sub << rect_hole
    ref_h2.move((0.425, 0.55))
    
    # Bottom arm windows
    ref_h3 = c_sub << rect_hole
    ref_h3.move((-0.425, -0.55))
    
    ref_h4 = c_sub << rect_hole
    ref_h4.move((0.425, -0.55))


    # ---------------------------------------------------------
    # 3. Final Boolean Composition
    # ---------------------------------------------------------
    # Subtract the rectangular window forms from the main solid pathways
    final_device = gf.boolean(c_add, c_sub, operation="not", layer=layer)
    
    c << final_device
    return c

if __name__ == "__main__":
    # Instantiate the component
    c = raceway_mzi_structure()
    
    # Actively generate and write the required GDS file to disk
    c.write_gds("raceway_mzi.gds")