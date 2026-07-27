import gdsfactory as gf

@gf.cell
def mzi_racetrack_device():
    """
    Creates a device reproducing the attached image:
    A racetrack-shaped outer ring containing a heater-integrated MZI.
    Footprint constraint: 3um x 5.5um.
    """
    c = gf.Component()
    layer = (1, 0)

    # --- Geometry Parameters ---
    # Overall Dimensions
    total_width = 5.5
    total_height = 3.0
    
    # Ring Geometry
    # A racetrack is defined by a central rectangle and two semi-circles.
    r_outer = total_height / 2.0  # 1.5um
    rect_width = total_width - total_height  # 5.5 - 3.0 = 2.5um straight section
    
    ring_thickness = 0.55
    r_inner = r_outer - ring_thickness
    
    # MZI Parameters
    arm_y_offset = 0.6          # Y-shift for the interferometer arms
    heater_width = 1.2
    heater_height = 0.55
    wg_width = 0.45             # Width of the connecting arms
    
    # --- 1. Construct the Racetrack Ring ---
    
    def make_pill(radius, width_flat, layer):
        """Creates a flattened 'pill' shape using boolean union of circles and rect."""
        # Create a temporary component to hold references
        temp = gf.Component()
        
        # 1. Create Primitives
        c_circle = gf.components.circle(radius=radius, layer=layer)
        c_rect = gf.components.rectangle(size=(width_flat, 2 * radius), centered=True, layer=layer)
        
        # 2. Add References and Position them
        refs = []
        
        # Left Circle
        r_left = temp << c_circle
        r_left.move((-width_flat / 2, 0))
        refs.append(r_left)
        
        # Right Circle
        r_right = temp << c_circle
        r_right.move((width_flat / 2, 0))
        refs.append(r_right)
        
        # Center Rectangle
        r_rect = temp << c_rect
        refs.append(r_rect)
        
        # 3. Boolean Union (passing the list of references explicitly)
        return gf.boolean(refs, [], operation="or", layer=layer)

    # Generate Outer and Inner Pills
    outer_pill = make_pill(r_outer, rect_width, layer)
    inner_pill = make_pill(r_inner, rect_width, layer)
    
    # Create the Ring (Outer - Inner)
    # gf.boolean can accept Component objects directly
    ring = gf.boolean(outer_pill, inner_pill, operation="not", layer=layer)
    c << ring

    # --- 2. Construct the Heaters ---
    
    # Create the Heater Body Primitive
    heater_body = gf.components.rectangle(size=(heater_width, heater_height), centered=True, layer=layer)
    
    # Create the Holes (Windows)
    hole_size = 0.25
    hole_sep = 0.35
    
    # We use a temp component to position the hole references
    temp_holes = gf.Component()
    hole_rect = gf.components.rectangle(size=(hole_size, hole_size), centered=True, layer=layer)
    
    h1 = temp_holes << hole_rect
    h1.move((-hole_sep, 0))
    
    h2 = temp_holes << hole_rect
    h2.move((hole_sep, 0))
    
    # Subtract holes from body using explicit reference lists
    # A = Body (Component), B = List of Hole References
    heater_element = gf.boolean(heater_body, [h1, h2], operation="not", layer=layer)

    # Place Top Heater
    h_top = c << heater_element
    h_top.move((0, arm_y_offset))
    
    # Place Bottom Heater
    h_bot = c << heater_element
    h_bot.move((0, -arm_y_offset))

    # --- 3. Construct Connecting Arms (S-Bends) ---
    # Arms connect the heater ends to the inner apex of the ring.
    
    # Coordinate calculations
    # The inner wall of the ring at y=0 is at x = +/- (rect_width/2 + r_inner)
    x_ring_inner_apex = (rect_width / 2) + r_inner
    x_heater_edge = heater_width / 2
    
    # S-Bend Dimensions
    dx = x_ring_inner_apex - x_heater_edge
    dy = arm_y_offset
    
    xs_arm = gf.cross_section.cross_section(width=wg_width, layer=layer)
    
    # Create S-bend primitives
    # bend_s creates a path from (0,0) to (size[0], size[1])
    bend_up = gf.components.bend_s(size=(dx, dy), cross_section=xs_arm)
    bend_down = gf.components.bend_s(size=(dx, -dy), cross_section=xs_arm)
    
    # 1. Top Left Connection
    # Connects Ring Left (-x_apex, 0) -> Heater Left (-x_heater, y_off)
    btl = c << bend_up
    btl.move((-x_ring_inner_apex, 0))
    
    # 2. Top Right Connection
    # Connects Heater Right (x_heater, y_off) -> Ring Right (x_apex, 0)
    btr = c << bend_down
    btr.move((x_heater_edge, arm_y_offset))

    # 3. Bottom Left Connection
    # Connects Ring Left (-x_apex, 0) -> Heater Bottom (-x_heater, -y_off)
    bbl = c << bend_down
    bbl.move((-x_ring_inner_apex, 0))

    # 4. Bottom Right Connection
    # Connects Heater Right (x_heater, -y_off) -> Ring Right (x_apex, 0)
    bbr = c << bend_up
    bbr.move((x_heater_edge, -arm_y_offset))

    return c

if __name__ == "__main__":
    device = mzi_racetrack_device()
    device.show()
    device.write_gds("mzi_racetrack.gds")