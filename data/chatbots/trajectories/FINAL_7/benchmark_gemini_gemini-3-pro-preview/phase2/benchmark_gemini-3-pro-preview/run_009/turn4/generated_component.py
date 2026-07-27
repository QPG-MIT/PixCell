import gdsfactory as gf
import numpy as np

@gf.cell
def device_iter4():
    """
    Racetrack resonator with flared internal suspended perforated beams.
    Refined based on target image:
    - Implements 'flared' arms that widen as they connect the central beams to the curved ring wall.
    - Adjusts dimensions to match the ~5.5um x 3.0um footprint and visual proportions.
    """
    c = gf.Component()
    
    # ==========================================
    # 1. Dimensions & Parameters
    # ==========================================
    layer = (1, 0)
    
    # Device Constraints
    # Target Footprint: ~5.5um x 3.0um
    w_device = 5.5
    h_device = 3.0
    
    # Ring Geometry
    # Adjusted thickness to allow for internal structures
    ring_width = 0.6
    r_outer = h_device / 2.0                 # 1.5
    r_inner = r_outer - ring_width           # 0.9 (Radius of the inner void at the bend)
    l_straight = w_device - 2 * r_outer      # 2.5
    
    # Center x-coordinates of the semicircles
    xc_right = l_straight / 2.0              # 1.25
    
    # Internal Beam Geometry
    # The beams are suspended centrally and contain rectangular holes
    beam_h = 0.35                            # Height of the straight rectangular beam section
    beam_gap = 0.3                           # Vertical gap between top and bottom beams
    y_beam_off = (beam_gap + beam_h) / 2.0   # Y-center of top beam
    
    # Y limits of the straight beam section (for polygon connection points)
    y_beam_bot = y_beam_off - beam_h / 2.0   # Inner edge Y
    y_beam_top = y_beam_off + beam_h / 2.0   # Outer edge Y
    
    # X limits
    # The straight rectangular section holding the holes ends here
    x_beam_end = 0.85
    
    # Hole Parameters
    hole_w = 0.45
    hole_h = 0.15
    hole_pitch = 0.6                         # Center-to-center spacing
    
    # ==========================================
    # 2. Build Ring (Path Method)
    # ==========================================
    r_path = r_outer - ring_width / 2.0
    
    p = gf.Path()
    p.append(gf.path.straight(length=l_straight/2))
    p.append(gf.path.arc(radius=r_path, angle=180))
    p.append(gf.path.straight(length=l_straight))
    p.append(gf.path.arc(radius=r_path, angle=180))
    p.append(gf.path.straight(length=l_straight/2))
    
    xs_ring = gf.cross_section.cross_section(width=ring_width, layer=layer)
    ring = c << gf.path.extrude(p, cross_section=xs_ring)
    ring.movey(-r_path) # Center the ring vertically
    
    # ==========================================
    # 3. Build Beams (Rectangular parts with holes)
    # ==========================================
    def create_beam():
        temp = gf.Component()
        # Main solid body
        body = temp << gf.components.rectangle(size=(2*x_beam_end, beam_h), centered=True, layer=layer)
        
        # Holes
        h1 = temp << gf.components.rectangle(size=(hole_w, hole_h), centered=True, layer=layer)
        h1.movex(-hole_pitch/2)
        h2 = temp << gf.components.rectangle(size=(hole_w, hole_h), centered=True, layer=layer)
        h2.movex(hole_pitch/2)
        
        # Subtract holes from body
        holes = gf.boolean(h1, h2, operation="or", layer=layer)
        final = gf.boolean(body, holes, operation="not", layer=layer)
        return final

    beam_shape = create_beam()
    
    # Place Top Beam
    b1 = c << beam_shape
    b1.movey(y_beam_off)
    
    # Place Bottom Beam
    b2 = c << beam_shape
    b2.movey(-y_beam_off)
    
    # ==========================================
    # 4. Build Flared Arms (Polygons)
    # ==========================================
    # Create the tapered/flared connection from the beam ends to the curved inner wall.
    # The flare creates the widening gap effect seen in the target.
    
    # Y-coordinates on the arc where the arm attaches
    # These are wider than the beam Ys to create the flare
    y_flare_top = 0.8   # Outer attachment point on the arc
    y_flare_bot = 0.25  # Inner attachment point on the arc (widens the gap)
    
    # Helper to find x on the right arc inner wall given y
    # Equation of inner circle: (x - xc)^2 + y^2 = r_inner^2
    def get_arc_right_x(y):
        y_clipped = np.clip(np.abs(y), 0, r_inner)
        val = r_inner**2 - y_clipped**2
        return xc_right + np.sqrt(val)
        
    # Generate points for Top-Right Arm polygon
    # 1. Start at top-right corner of the rectangular beam
    # 2. Trace along the inner arc boundary from the top flare point down to the bottom flare point
    # 3. End at bottom-right corner of the rectangular beam
    
    # Sample the arc edge
    ys_arc = np.linspace(y_flare_top, y_flare_bot, 20)
    arc_points = [(get_arc_right_x(y), y) for y in ys_arc]
    
    # Construct polygon points
    poly_pts_tr = [(x_beam_end, y_beam_top)] + arc_points + [(x_beam_end, y_beam_bot)]
    
    # Add Top-Right Arm
    c.add_polygon(poly_pts_tr, layer=layer)
    
    # Add Bottom-Right Arm (Mirror Y)
    poly_pts_br = [(x, -y) for x, y in poly_pts_tr]
    c.add_polygon(poly_pts_br, layer=layer)
    
    # Add Top-Left Arm (Mirror X)
    poly_pts_tl = [(-x, y) for x, y in poly_pts_tr]
    c.add_polygon(poly_pts_tl, layer=layer)
    
    # Add Bottom-Left Arm (Mirror X and Y)
    poly_pts_bl = [(-x, y) for x, y in poly_pts_br]
    c.add_polygon(poly_pts_bl, layer=layer)

    return c

if __name__ == "__main__":
    device = device_iter4()
    device.show()
    device.write_gds("device_iter4.gds")