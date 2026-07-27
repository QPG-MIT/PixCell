import gdsfactory as gf

@gf.cell
def device_recreated():
    """
    Recreates the device geometry:
    - Racetrack ring (constructed via Path)
    - Internal suspended beams with cutouts (constructed via Boolean)
    - Tapered tethers connecting beams to ring
    """
    c = gf.Component()
    
    # ==========================================
    # 1. Geometry Parameters
    # ==========================================
    layer = (1, 0)
    
    # Device Footprint Approx: 5.5 x 3.0 um
    width_outer = 5.5
    height_outer = 3.0
    ring_width = 0.6
    
    # Derived Ring Parameters
    r_outer = height_outer / 2.0              # 1.5
    r_center = r_outer - ring_width / 2.0     # 1.2
    l_straight = width_outer - 2 * r_outer    # 2.5
    
    # Internal Beam Parameters
    beam_w = 1.4
    beam_h = 0.4
    beam_gap = 0.4
    beam_y_center = (beam_gap + beam_h) / 2.0
    
    # Hole (Cutout) Parameters
    hole_w = 0.4
    hole_h = 0.15
    hole_pitch = 0.5
    
    # ==========================================
    # 2. Build Outer Ring (Parametric Path)
    # ==========================================
    # We build the racetrack path starting from bottom-center
    p = gf.Path()
    p.append(gf.path.straight(length=l_straight/2))  # Bottom-right straight
    p.append(gf.path.arc(radius=r_center, angle=180)) # Right curve
    p.append(gf.path.straight(length=l_straight))    # Top straight
    p.append(gf.path.arc(radius=r_center, angle=180)) # Left curve
    p.append(gf.path.straight(length=l_straight/2))  # Bottom-left straight
    
    # Extrude the path
    xs_ring = gf.cross_section.cross_section(width=ring_width, layer=layer)
    ring = c << gf.path.extrude(p, cross_section=xs_ring)
    
    # Center the ring (Path construction naturally offsets Y by radius)
    ring.movey(-r_center)
    
    # ==========================================
    # 3. Build Internal Beams (Safe Boolean)
    # ==========================================
    def make_beam():
        temp = gf.Component()
        
        # Create primitives
        body = temp << gf.components.rectangle(size=(beam_w, beam_h), centered=True, layer=layer)
        
        h1 = temp << gf.components.rectangle(size=(hole_w, hole_h), centered=True, layer=layer)
        h1.movex(-hole_pitch/2)
        
        h2 = temp << gf.components.rectangle(size=(hole_w, hole_h), centered=True, layer=layer)
        h2.movex(hole_pitch/2)
        
        # Step 1: Merge holes (Pass single references, not a list)
        holes_merged = gf.boolean(h1, h2, operation="or", layer=layer)
        
        # Step 2: Subtract holes from body
        beam_geo = gf.boolean(body, holes_merged, operation="not", layer=layer)
        return beam_geo

    beam_comp = make_beam()
    
    # Place Top Beam
    top_beam = c << beam_comp
    top_beam.movey(beam_y_center)
    
    # Place Bottom Beam
    bot_beam = c << beam_comp
    bot_beam.movey(-beam_y_center)
    
    # ==========================================
    # 4. Connecting Arms (Tethers)
    # ==========================================
    # Define connection points
    # Overlap slightly with beam and ring for connectivity
    x_beam_edge = beam_w / 2.0 - 0.05
    x_ring_edge = l_straight / 2.0 - 0.05 # Connect near the start of the arc
    
    # Define Width Transition (Taper)
    xs_beam = gf.cross_section.cross_section(width=beam_h, layer=layer)
    xs_ring_conn = gf.cross_section.cross_section(width=0.4, layer=layer) # Arms narrow slightly or merge
    
    trans = gf.path.transition(xs_beam, xs_ring_conn)
    
    # Create 4 arms
    # Top Right
    ptr = gf.Path([(x_beam_edge, beam_y_center), (x_ring_edge, 0.2)])
    c << gf.path.extrude_transition(ptr, trans)
    
    # Bottom Right
    pbr = gf.Path([(x_beam_edge, -beam_y_center), (x_ring_edge, -0.2)])
    c << gf.path.extrude_transition(pbr, trans)
    
    # Top Left (Mirror X)
    ptl = gf.Path([(-x_beam_edge, beam_y_center), (-x_ring_edge, 0.2)])
    c << gf.path.extrude_transition(ptl, trans)
    
    # Bottom Left (Mirror X)
    pbl = gf.Path([(-x_beam_edge, -beam_y_center), (-x_ring_edge, -0.2)])
    c << gf.path.extrude_transition(pbl, trans)
    
    return c

if __name__ == "__main__":
    device = device_recreated()
    device.show()
    device.write_gds("device_recreated.gds")