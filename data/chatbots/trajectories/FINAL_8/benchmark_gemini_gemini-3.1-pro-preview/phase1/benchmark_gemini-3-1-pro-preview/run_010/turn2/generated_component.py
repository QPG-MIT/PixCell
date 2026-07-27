import gdsfactory as gf

@gf.cell
def apodized_directional_coupler() -> gf.Component:
    """
    Creates an apodized directional coupler matching the specified footprint (120.0 x 4.0 um).
    Uses a fan-out geometry for the top and bottom groups to perfectly match the target image:
    waveguides merge into a solid block in the center coupling region and fan out at the ends.
    """
    c = gf.Component("apodized_directional_coupler")

    # --- Geometric Parameters ---
    # Overall dimensions to match the [120.0, 4.0] footprint
    L_total = 120.0
    L_center = 80.0
    L_bend = (L_total - L_center) / 2.0  # 20.0
    
    # Widths and gaps (tuned for visual proportions)
    w_thin = 0.06
    gap_thin = 0.06
    w_thick = 0.60
    c_gap = 0.10 # Coupling gap between center bus and outer buses
    
    layer = (1, 0)

    # --- Assembly Helpers ---
    def add_straight_lane(y_pos: float, width: float):
        xs = gf.cross_section.cross_section(width=width, layer=layer)
        lane = c << gf.components.straight(length=L_total, cross_section=xs)
        lane.move((-L_total / 2.0, y_pos))

    def add_bent_lane(y_center: float, width: float, dy: float):
        xs = gf.cross_section.cross_section(width=width, layer=layer)
        
        # Center straight segment
        str_geom = c << gf.components.straight(length=L_center, cross_section=xs)
        str_geom.move((-L_center / 2.0, y_center))
        
        # Right bend (Outward)
        bend_r = c << gf.components.bend_s(size=(L_bend, dy), cross_section=xs)
        bend_r.connect('o1', str_geom.ports['o2'])
        
        # Left bend (Outward)
        # The size uses -dy so when connecting o2 to o1 (backwards), the geometric translation mirrors correctly
        bend_l = c << gf.components.bend_s(size=(L_bend, -dy), cross_section=xs)
        bend_l.connect('o2', str_geom.ports['o1'])

    # --- 1. Center Bus ---
    # 5 thin waveguides uniformly spaced, going straight across
    pitch_thin = w_thin + gap_thin
    y_center_bus = [i * pitch_thin for i in range(-2, 3)]
    
    for y in y_center_bus:
        add_straight_lane(y, w_thin)

    # --- 2. Top Bus Calculations ---
    top_edge_center_bus = y_center_bus[-1] + w_thin / 2.0
    bottom_edge_top_bus = top_edge_center_bus + c_gap
    
    # A. Center straight section: 1 thick line and 5 thin lines merged (gap = 0 forms the solid block)
    y_top_thick_c = bottom_edge_top_bus + w_thick / 2.0
    
    y_top_thin_c = []
    current_y = bottom_edge_top_bus + w_thick + w_thin / 2.0
    for _ in range(5):
        y_top_thin_c.append(current_y)
        current_y += w_thin
        
    # B. End sections: Fan out to standard pitch (gap = gap_thin) filling up to y = 2.0
    target_y_max = 2.0
    y_top_thin_end = []
    current_end_y = target_y_max - w_thin / 2.0
    for _ in range(5):
        y_top_thin_end.insert(0, current_end_y) # Insert at 0 to match bottom-up order
        current_end_y -= pitch_thin
        
    y_top_thick_end = y_top_thin_end[0] - w_thin / 2.0 - gap_thin - w_thick / 2.0
    
    # Calculate required dy vertical displacement for each lane
    dy_top_thick = y_top_thick_end - y_top_thick_c
    dy_top_thin = [end - c_y for end, c_y in zip(y_top_thin_end, y_top_thin_c)]
    
    # --- Build Top Bus ---
    add_bent_lane(y_top_thick_c, w_thick, dy_top_thick)
    for y_c, dy in zip(y_top_thin_c, dy_top_thin):
        add_bent_lane(y_c, w_thin, dy)

    # --- 3. Build Bottom Bus (Symmetric Mirror) ---
    add_bent_lane(-y_top_thick_c, w_thick, -dy_top_thick)
    for y_c, dy in zip(y_top_thin_c, dy_top_thin):
        add_bent_lane(-y_c, w_thin, -dy)

    return c

if __name__ == "__main__":
    device = apodized_directional_coupler()
    device.write_gds("apodized_directional_coupler.gds")