import gdsfactory as gf

@gf.cell
def segmented_straight_comp(num_segments: int, segment_width: float, segment_gap: float, width: float, layer: tuple) -> gf.Component:
    """Creates a segmented straight waveguide component."""
    comp = gf.Component()
    
    # Calculate total length of the segmented part for port placement
    total_length = num_segments * segment_width + (num_segments - 1) * segment_gap
    
    # Create and place individual rectangles
    for i in range(num_segments):
        seg_ref = comp << gf.components.rectangle(size=(segment_width, width), layer=layer, centered=True)
        # Position each segment's center. The first segment starts at x=segment_width/2,
        # so its left edge is at x=0.
        seg_ref.x = i * (segment_width + segment_gap) + segment_width / 2
    
    # Add ports to the component. Port o1 is at the effective start of the segments, o2 at the end.
    comp.add_port("o1", center=(0, 0), width=width, orientation=180, layer=layer, port_type="optical")
    comp.add_port("o2", center=(total_length, 0), width=width, orientation=0, layer=layer, port_type="optical")
    
    return comp

@gf.cell
def make_inner_waveguide(
    xs: gf.CrossSection,
    num_segments: int, segment_width: float, segment_gap: float,
    L_smooth_straight: float, R_bend: float, L_vertical_connect: float,
    L_taper: float, point_width: float,
    curve_down: bool = True # If True, bends down (for top); if False, bends up (for bottom)
) -> gf.Component:
    """Creates a composite inner waveguide with segments, straight, bends, and taper."""
    comp = gf.Component()
    
    # 1. Segmented part
    segments = comp << segmented_straight_comp(num_segments, segment_width, segment_gap, xs.width, xs.layer)
    
    # 2. Smooth straight after segments
    s_smooth = comp << gf.components.straight(length=L_smooth_straight, cross_section=xs)
    s_smooth.connect("o1", segments.ports["o2"])
    
    # 3. Bend sequence for U-turn
    angle1 = -90 if curve_down else 90 # First bend: down or up
    angle2 = 90 if curve_down else -90 # Second bend: left or right from previous direction
    
    b1 = comp << gf.components.bend_euler(radius=R_bend, angle=angle1, cross_section=xs)
    b1.connect("o1", s_smooth.ports["o2"])
    
    sv = comp << gf.components.straight(length=L_vertical_connect, cross_section=xs)
    sv.connect("o1", b1.ports["o2"])
    
    b2 = comp << gf.components.bend_euler(radius=R_bend, angle=angle2, cross_section=xs)
    b2.connect("o1", sv.ports["o2"])
    
    # 4. End taper
    t_end = comp << gf.components.taper(length=L_taper, width1=xs.width, width2=point_width, cross_section=xs)
    t_end.connect("o1", b2.ports["o2"])

    # Expose main ports of this composite component
    comp.add_port("o1", port=segments.ports["o1"]) # Leftmost part of segments
    comp.add_port("o2", port=t_end.ports["o2"])   # Rightmost part of taper (pointed end)
    
    return comp

@gf.cell
def make_outer_waveguide_unit(
    xs: gf.CrossSection, L_taper: float, point_width: float,
    L_straight: float, R_bend: float, angle: float = -180 # -180 for top (curves down), 180 for bottom (curves up)
) -> gf.Component:
    """Creates a composite outer waveguide with taper, straight, and 180-deg bend."""
    comp = gf.Component()
    
    # 1. Start taper (starts pointed, ends wide)
    t_start = comp << gf.components.taper(length=L_taper, width1=point_width, width2=xs.width, cross_section=xs)
    
    # 2. Middle straight section
    s_mid = comp << gf.components.straight(length=L_straight, cross_section=xs)
    s_mid.connect("o1", t_start.ports["o2"])
    
    # 3. 180-degree bend (forms the U-turn)
    bend_180 = comp << gf.components.bend_euler(radius=R_bend, angle=angle, cross_section=xs)
    bend_180.connect("o1", s_mid.ports["o2"])
    
    # Expose main ports of this composite component
    comp.add_port("o1", port=t_start.ports["o1"]) # Leftmost pointed end
    comp.add_port("o2", port=bend_180.ports["o2"]) # Output of the 180-deg bend
    
    return comp

@gf.cell
def my_device() -> gf.Component:
    """Recreates the complex waveguide device from the image."""
    c = gf.Component("my_device")
    
    # Define layers and default cross-sections
    LAYER = (1, 0) 
    
    # Global dimensions from footprint
    total_width = 18.24
    total_height = 0.7
    
    # Cross-section widths and vertical gaps (estimated)
    w_center = 0.05
    w_inner = 0.08
    w_outer = 0.15
    g1 = 0.05 # Gap between central line and inner
    g2 = 0.05 # Gap between inner and outer

    # Parameters for inner waveguides
    num_segments_inner = 25
    segment_width_inner = 0.26
    segment_gap_inner = 0.1
    L_smooth_straight_inner = 1.0
    R_inner_bend = 0.15
    L_vertical_inner_connect = 0.05
    L_taper_inner = 0.3
    point_width_inner = 0.01

    # Parameters for outer waveguides (MOVED TO HERE)
    L_taper_outer = 0.8
    point_width_outer = 0.01
    L_straight_outer = 7.0
    R_outer_bend = 0.25 

    # Derived Y-coordinates for the centerlines of components (relative to (0,0) center)
    y_center_line = 0
    y_inner_top_mid = y_center_line + w_center/2 + g1 + w_inner/2
    y_inner_bottom_mid = -y_inner_top_mid
    y_outer_top_mid = y_center_line + w_center/2 + g1 + w_inner + g2 + w_outer/2
    y_outer_bottom_mid = -y_outer_top_mid

    # --- 1. Central Straight Line ---
    xs_center = gf.cross_section.cross_section(width=w_center, layer=LAYER)
    center_line_ref = c << gf.components.straight(length=total_width, cross_section=xs_center)
    center_line_ref.center = (0, y_center_line) # Center device horizontally and vertically

    # --- 2. Inner Segmented Waveguides ---
    # Fix: Set radius_min to accommodate R_inner_bend (0.15)
    xs_inner = gf.cross_section.cross_section(width=w_inner, layer=LAYER, radius_min=0.1) 
    
    # Top Inner Waveguide
    inner_top_cell = make_inner_waveguide(
        xs_inner, num_segments_inner, segment_width_inner, segment_gap_inner,
        L_smooth_straight_inner, R_inner_bend, L_vertical_inner_connect, L_taper_inner, point_width_inner,
        curve_down=True 
    )
    inner_top_ref = c << inner_top_cell
    # Place its leftmost port (o1) near the device's left edge. The point of the taper for the inner waveguide is on the right.
    # The inner_top_ref.ports["o1"] is the start of the segmented part, which is at x=0 of its own component.
    # We want the *component's* leftmost x to be around -total_width/2.
    # The inner_top_cell has its segmented part starting at x=0 (its "o1" port).
    # Its tapering end is at the end of the bend sequence, which is to the right.
    inner_top_ref.movex(-inner_top_ref.ports["o1"].x + (-total_width/2 + L_taper_outer * 0.5)) # L_taper_outer is now defined
    inner_top_ref.y = y_inner_top_mid


    # Bottom Inner Waveguide (Mirror image of top inner)
    # The bottom one has segments on the right, tapering left.
    inner_bottom_cell = make_inner_waveguide(
        xs_inner, num_segments_inner, segment_width_inner, segment_gap_inner,
        L_smooth_straight_inner, R_inner_bend, L_vertical_inner_connect, L_taper_inner, point_width_inner,
        curve_down=False 
    )
    inner_bottom_ref = c << inner_bottom_cell
    inner_bottom_ref.mirror(p1=(0,0), p2=(1,0)) # Mirror across X-axis
    inner_bottom_ref.mirror(p1=(0,0), p2=(0,1)) # Mirror across Y-axis to put segments on the right
    
    # The inner_bottom_ref.ports["o1"] is now its rightmost port (original segments start).
    inner_bottom_ref.movex(-inner_bottom_ref.ports["o1"].x + (total_width/2 - L_taper_outer * 0.5)) # L_taper_outer is now defined
    inner_bottom_ref.y = y_inner_bottom_mid

    # --- 3. Outer U-shaped Waveguides ---
    # Fix: Set radius_min to accommodate R_outer_bend (0.25)
    xs_outer = gf.cross_section.cross_section(width=w_outer, layer=LAYER, radius_min=0.2) 
    
    # Top Outer Waveguide
    outer_top_cell = make_outer_waveguide_unit(
        xs_outer, L_taper_outer, point_width_outer, L_straight_outer, R_outer_bend, angle=-180
    )
    outer_top_ref = c << outer_top_cell
    # Place its leftmost port (o1, the pointed end) at the device's far left edge
    outer_top_ref.movex(-outer_top_ref.ports["o1"].x - total_width/2)
    outer_top_ref.y = y_outer_top_mid


    # Bottom Outer Waveguide (Mirror image of top outer)
    outer_bottom_cell = make_outer_waveguide_unit(
        xs_outer, L_taper_outer, point_width_outer, L_straight_outer, R_outer_bend, angle=180 # Curves up
    )
    outer_bottom_ref = c << outer_bottom_cell
    outer_bottom_ref.mirror(p1=(0,0), p2=(1,0)) # Mirror across X-axis
    outer_bottom_ref.mirror(p1=(0,0), p2=(0,1)) # Mirror across Y-axis to put taper on the right and bend on the left

    # Place its (now rightmost) port (o1) at the device's far right edge
    outer_bottom_ref.movex(-outer_bottom_ref.ports["o1"].x + total_width/2)
    outer_bottom_ref.y = y_outer_bottom_mid

    # Center the entire component after all placements
    c.center = (0,0)

    # Validate overall footprint (optional, for debugging)
    # c.flatten() # Flatten to get a single polygon for bounding box check
    # bbox = c.bbox # Get bounding box
    # actual_width = bbox[1, 0] - bbox[0, 0]
    # actual_height = bbox[1, 1] - bbox[0, 1]
    # print(f"Actual device width: {actual_width:.2f} um")
    # print(f"Actual device height: {actual_height:.2f} um")

    return c

if __name__ == "__main__":
    device = my_device()
    device.write_gds("complex_waveguide.gds")
    # To view the GDS file, uncomment the line below and ensure you have a GDS viewer installed
    # device.show()