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
    
    # Add ports to the component. Port o1 is at the effective start of the segments (left), o2 at the end (right).
    comp.add_port("o1", center=(0, 0), width=width, orientation=180, layer=layer, port_type="optical")
    comp.add_port("o2", center=(total_length, 0), width=width, orientation=0, layer=layer, port_type="optical")
    
    return comp

@gf.cell
def make_inner_waveguide_unit(
    xs: gf.CrossSection,
    num_segments: int, segment_width: float, segment_gap: float,
    L_taper_start: float, point_width_start: float,
    L_straight_before_bend: float,
    R_bend: float, L_vertical_connect: float,
    L_straight_after_bend: float,
    angle1: float = -90, # First 90-deg bend angle (e.g., -90 for East to South)
    angle2: float = -90  # Second 90-deg bend angle (e.g., -90 for South to West)
) -> gf.Component:
    """
    Creates a composite inner waveguide unit with taper (o1), straight, U-turn, straight, segments (o2).
    This unit is designed to represent the TOP inner waveguide from the image,
    where the pointed end (o1) is on the left, and the segmented end (o2) is also on the left.
    """
    comp = gf.Component()
    
    # 1. Start taper (starts pointed, ends wide)
    # The taper starts at x=0, pointing left (orientation 180)
    t_start = comp << gf.components.taper(length=L_taper_start, width1=point_width_start, width2=xs.width, cross_section=xs)
    # The taper's o1 is at (0,0) facing 180 (left). Its o2 is at (L_taper_start, 0) facing 0 (right).
    
    # 2. Straight section before U-turn (extends right from taper)
    s1 = comp << gf.components.straight(length=L_straight_before_bend, cross_section=xs)
    s1.connect("o1", t_start.ports["o2"]) # Connect to right end of taper, so s1 extends further right.

    # 3. First 90-degree bend (e.g., East to South for angle=-90)
    b1 = comp << gf.components.bend_euler(radius=R_bend, angle=angle1, cross_section=xs)
    b1.connect("o1", s1.ports["o2"]) # Connect to right end of s1.

    # 4. Vertical straight connection
    sv = comp << gf.components.straight(length=L_vertical_connect, cross_section=xs)
    sv.connect("o1", b1.ports["o2"]) # Connect to end of b1.

    # 5. Second 90-degree bend (e.g., South to West for angle=-90 from current orientation)
    b2 = comp << gf.components.bend_euler(radius=R_bend, angle=angle2, cross_section=xs)
    b2.connect("o1", sv.ports["o2"]) # Connect to end of sv.

    # 6. Second straight section (extends left from U-turn)
    s2 = comp << gf.components.straight(length=L_straight_after_bend, cross_section=xs)
    s2.connect("o1", b2.ports["o2"]) # Connect to end of b2.

    # 7. Segmented part (connects to left end of s2)
    segments = comp << segmented_straight_comp(num_segments, segment_width, segment_gap, xs.width, xs.layer)
    # Connect the right port of the segments component (o2) to the left port of s2 (o2).
    segments.connect("o2", s2.ports["o2"]) 

    # Expose ports: o1 is the pointed end (leftmost), o2 is the leftmost part of segments.
    comp.add_port("o1", port=t_start.ports["o1"]) # Pointed end, at (0,0) of this component
    comp.add_port("o2", port=segments.ports["o1"]) # Leftmost part of segments

    return comp

@gf.cell
def make_outer_waveguide_unit(
    xs: gf.CrossSection, L_taper: float, point_width: float,
    L_straight: float, R_bend: float, angle: float = -180 # -180 for top (curves down), 180 for bottom (curves up)
) -> gf.Component:
    """Creates a composite outer waveguide with taper (o1), straight, and 180-deg bend (o2)."""
    comp = gf.Component()
    
    # 1. Start taper (starts pointed, ends wide)
    t_start = comp << gf.components.taper(length=L_taper, width1=point_width, width2=xs.width, cross_section=xs)
    # t_start.ports["o1"] is the pointed end, at (0,0) of the component, facing 180 (left)
    
    # 2. Middle straight section
    s_mid = comp << gf.components.straight(length=L_straight, cross_section=xs)
    s_mid.connect("o1", t_start.ports["o2"]) # Connects to the right end of the taper
    
    # 3. 180-degree bend (forms the U-turn)
    bend_180 = comp << gf.components.bend_euler(radius=R_bend, angle=angle, cross_section=xs)
    bend_180.connect("o1", s_mid.ports["o2"]) # Connects to the right end of the straight
    
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
    w_outer = 0.08 # Adjusted for vertical fit
    g1 = 0.05 # Gap between central line and inner
    g2 = 0.05 # Gap between inner and outer

    # Parameters for inner waveguides
    num_segments_inner = 10 # Adjusted
    segment_width_inner = 0.26
    segment_gap_inner = 0.1
    L_taper_inner = 0.3
    point_width_inner = 0.01
    L_straight_before_inner_bend = 1.0 # New parameter
    R_inner_bend = 0.035 # Adjusted for vertical fit
    L_vertical_inner_connect = 0.02 # Adjusted
    L_straight_after_inner_bend = 0.5 # New parameter

    # Parameters for outer waveguides
    L_taper_outer = 0.8
    point_width_outer = 0.01
    L_straight_outer = 7.0
    R_outer_bend = 0.065 # Adjusted for vertical fit

    # Derived Y-coordinates for the centerlines of components (relative to (0,0) center)
    y_center_line = 0
    y_inner_top_mid = y_center_line + w_center/2 + g1 + w_inner/2 # = 0.115
    y_inner_bottom_mid = -y_inner_top_mid
    y_outer_top_mid = y_inner_top_mid + w_inner/2 + g2 + w_outer/2 # = 0.245
    y_outer_bottom_mid = -y_outer_top_mid

    # --- 1. Central Straight Line ---
    xs_center = gf.cross_section.cross_section(width=w_center, layer=LAYER)
    center_line_ref = c << gf.components.straight(length=total_width, cross_section=xs_center)
    center_line_ref.center = (0, y_center_line) # Center device horizontally and vertically

    # --- 2. Inner Segmented Waveguides ---
    # Set radius_min to accommodate R_inner_bend (0.035). Removed 'npoints'.
    xs_inner = gf.cross_section.cross_section(width=w_inner, layer=LAYER, radius_min=0.03) 
    
    # Top Inner Waveguide: Pointed left, segments left, U-turn curves down-then-left
    inner_top_cell = make_inner_waveguide_unit(
        xs_inner, num_segments_inner, segment_width_inner, segment_gap_inner,
        L_taper_inner, point_width_inner, L_straight_before_inner_bend,
        R_inner_bend, L_vertical_inner_connect, L_straight_after_inner_bend,
        angle1=-90, angle2=-90 # East -> South, then South -> West
    )
    inner_top_ref = c << inner_top_cell
    # Place its leftmost port (o1, the pointed end) at the calculated x-position
    inner_top_ref.x = -total_width/2 + L_taper_outer # Align with start of outer taper
    inner_top_ref.y = y_inner_top_mid

    # Bottom Inner Waveguide: Mirror image of top inner (pointed right, segments right, U-turn curves up-then-right)
    inner_bottom_ref = c << inner_top_cell # Reuse the same cell
    inner_bottom_ref.rotate(180) # Rotate 180 degrees to achieve desired symmetry
    # Its 'o1' port is now effectively the rightmost point. Place it at the calculated x-position.
    inner_bottom_ref.x = total_width/2 - L_taper_outer # Align with end of outer taper
    inner_bottom_ref.y = y_inner_bottom_mid

    # --- 3. Outer U-shaped Waveguides ---
    # Set radius_min to accommodate R_outer_bend (0.065). Removed 'npoints'.
    xs_outer = gf.cross_section.cross_section(width=w_outer, layer=LAYER, radius_min=0.05) 
    
    # Top Outer Waveguide: Pointed left, straight right, then bend -180 (curves down)
    outer_top_cell = make_outer_waveguide_unit(
        xs_outer, L_taper_outer, point_width_outer, L_straight_outer, R_outer_bend, angle=-180
    )
    outer_top_ref = c << outer_top_cell
    # Place its leftmost port (o1, the pointed end) at the device's far left edge
    outer_top_ref.x = -total_width/2
    outer_top_ref.y = y_outer_top_mid

    # Bottom Outer Waveguide: Pointed right, straight left, then bend 180 (curves up)
    outer_bottom_ref = c << outer_top_cell # Reuse the same cell
    outer_bottom_ref.rotate(180) # Rotate 180 degrees
    # Its 'o1' port is now effectively the rightmost point. Place it at the device's far right edge.
    outer_bottom_ref.x = total_width/2
    outer_bottom_ref.y = y_outer_bottom_mid

    # Center the entire component after all placements (optional, but good practice)
    c.center = (0,0)

    # Optional: Validate overall footprint for debugging
    # c.flatten() 
    # bbox = c.bbox 
    # actual_width = bbox[1, 0] - bbox[0, 0]
    # actual_height = bbox[1, 1] - bbox[0, 1]
    # print(f"Target width: {total_width:.2f} um, Actual width: {actual_width:.2f} um")
    # print(f"Target height: {total_height:.2f} um, Actual height: {actual_height:.2f} um")

    return c

if __name__ == "__main__":
    device = my_device()
    device.write_gds("complex_waveguide.gds")
    # To view the GDS file, uncomment the line below and ensure you have a GDS viewer installed
    # device.show()