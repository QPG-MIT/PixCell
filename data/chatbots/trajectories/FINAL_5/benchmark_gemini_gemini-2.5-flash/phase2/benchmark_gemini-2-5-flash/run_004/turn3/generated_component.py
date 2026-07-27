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
        # Position each segment's center. The first segment's left edge is at x=0.
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
    R_bend: float, # Now for a 180-deg bend radius
    L_straight_after_bend: float,
) -> gf.Component:
    """
    Creates a composite inner waveguide unit with taper (o1), straight, 180-deg U-turn, straight, segments (o2).
    This unit represents the TOP inner waveguide from the image,
    where the pointed end (o1) is on the left, and the segmented end (o2) is also on the left.
    """
    comp = gf.Component()
    
    # 1. Start taper (starts pointed, ends wide). o1 is left, o2 is right.
    t_start = comp << gf.components.taper(length=L_taper_start, width1=point_width_start, width2=xs.width, cross_section=xs)
    
    # 2. Straight section before U-turn (extends right from taper)
    s1 = comp << gf.components.straight(length=L_straight_before_bend, cross_section=xs)
    s1.connect("o1", t_start.ports["o2"]) 

    # 3. 180-degree bend (U-turn). Input 'o1' faces East, output 'o2' faces West, curving down.
    # A positive angle for Euler bend is counter-clockwise. For top inner, it should curve down (clockwise).
    # So, angle=-180 is correct.
    bend_180 = comp << gf.components.bend_euler(radius=R_bend, angle=-180, cross_section=xs)
    bend_180.connect("o1", s1.ports["o2"]) 

    # 4. Straight section after U-turn (extends left from U-turn)
    s2 = comp << gf.components.straight(length=L_straight_after_bend, cross_section=xs)
    s2.connect("o1", bend_180.ports["o2"]) # Connect to output of bend_180, so s2 extends left.

    # 5. Segmented part (connects to left end of s2). Segments extend LEFT from s2.
    segments = comp << segmented_straight_comp(num_segments, segment_width, segment_gap, xs.width, xs.layer)
    # s2.ports["o2"] faces West (180).
    # segments.ports["o2"] faces East (0).
    # segments.connect("o2", s2.ports["o2"]) will rotate segments by 180 degrees.
    # After rotation: segments.o2 faces 180 (West), segments.o1 faces 0 (East).
    # So the *leftmost* part of the segments is now segments.o2.
    segments.connect("o2", s2.ports["o2"]) 

    # Expose ports: o1 is the pointed end (leftmost), o2 is the leftmost part of segments.
    comp.add_port("o1", port=t_start.ports["o1"]) 
    comp.add_port("o2", port=segments.ports["o2"]) # Corrected: Expose segments.o2 (leftmost part)

    return comp

@gf.cell
def make_outer_waveguide_unit(
    xs: gf.CrossSection, L_taper: float, point_width: float,
    L_straight: float, R_bend: float, angle: float = -180 # -180 for top (curves down), 180 for bottom (curves up)
) -> gf.Component:
    """Creates a composite outer waveguide with taper (o1), straight, and 180-deg bend (o2)."""
    comp = gf.Component()
    
    # 1. Start taper (starts pointed, ends wide). o1 is left, o2 is right.
    t_start = comp << gf.components.taper(length=L_taper, width1=point_width, width2=xs.width, cross_section=xs)
    
    # 2. Middle straight section (extends right from taper)
    s_mid = comp << gf.components.straight(length=L_straight, cross_section=xs)
    s_mid.connect("o1", t_start.ports["o2"]) 
    
    # 3. 180-degree bend (forms the U-turn). Input 'o1' faces East.
    # If angle=-180, curves down. Output 'o2' faces West.
    # If angle=180, curves up. Output 'o2' faces West.
    bend_180 = comp << gf.components.bend_euler(radius=R_bend, angle=angle, cross_section=xs)
    bend_180.connect("o1", s_mid.ports["o2"]) 
    
    # Expose main ports of this composite component
    comp.add_port("o1", port=t_start.ports["o1"]) # Leftmost pointed end
    comp.add_port("o2", port=bend_180.ports["o2"]) # Output of the 180-deg bend (rightmost part of the U)
    
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
    
    # Cross-section widths and vertical gaps (estimated from image)
    w_center = 0.05
    w_inner = 0.08
    w_outer = 0.08 
    g1 = 0.05 # Gap between central line and inner
    g2 = 0.05 # Gap between inner and outer

    # Parameters for outer waveguides (calculated in thinking process)
    L_taper_outer = 1.5
    point_width_outer = 0.001 
    L_straight_outer = 15.0 
    R_outer_bend = 0.87 

    # Parameters for inner waveguides (calculated in thinking process)
    num_segments_inner = 18 
    segment_width_inner = 0.1 
    segment_gap_inner = 0.05 
    L_taper_inner = 0.5 
    point_width_inner = 0.001 
    L_straight_before_inner_bend = 15.24 
    R_inner_bend = 0.5 
    L_straight_after_bend = 16.24 
    
    # Derived Y-coordinates for the centerlines of components (relative to (0,0) center)
    y_center_line = 0
    # y_inner_top_mid = centerline of central_line + half width of central line + gap1 + half width of inner waveguide
    y_inner_top_mid = y_center_line + w_center/2 + g1 + w_inner/2 
    y_inner_bottom_mid = -y_inner_top_mid
    # y_outer_top_mid = centerline of inner waveguide + half width of inner waveguide + gap2 + half width of outer waveguide
    y_outer_top_mid = y_inner_top_mid + w_inner/2 + g2 + w_outer/2 
    y_outer_bottom_mid = -y_outer_top_mid

    # --- 1. Central Straight Line ---
    xs_center = gf.cross_section.cross_section(width=w_center, layer=LAYER)
    center_line_ref = c << gf.components.straight(length=total_width, cross_section=xs_center)
    # Place its left end at -total_width/2, centered vertically.
    center_line_ref.x = -total_width / 2 
    center_line_ref.y = y_center_line

    # --- 2. Inner Segmented Waveguides ---
    # Set radius_min for inner cross-section to accommodate R_inner_bend (0.5).
    xs_inner = gf.cross_section.cross_section(width=w_inner, layer=LAYER, radius_min=0.2) 
    
    # Top Inner Waveguide: Pointed left, segments left, U-turn curves down-then-left
    inner_top_cell = make_inner_waveguide_unit(
        xs_inner, num_segments_inner, segment_width_inner, segment_gap_inner,
        L_taper_inner, point_width_inner, L_straight_before_inner_bend,
        R_inner_bend, L_straight_after_bend
    )
    inner_top_ref = c << inner_top_cell
    # Place its leftmost port (o1, the pointed end) at the calculated x-position
    inner_top_ref.x = -total_width/2 + L_taper_outer 
    inner_top_ref.y = y_inner_top_mid

    # Bottom Inner Waveguide: Mirror image of top inner (pointed right, segments right, U-turn curves up-then-right)
    inner_bottom_ref = c << inner_top_cell # Reuse the same cell
    inner_bottom_ref.rotate(180) # Rotate 180 degrees to achieve desired symmetry
    # Its 'o1' port is now effectively the rightmost point. Place it at the calculated x-position.
    inner_bottom_ref.x = total_width/2 - L_taper_outer 
    inner_bottom_ref.y = y_inner_bottom_mid

    # --- 3. Outer U-shaped Waveguides ---
    # Set radius_min for outer cross-section to accommodate R_outer_bend (0.87).
    xs_outer = gf.cross_section.cross_section(width=w_outer, layer=LAYER, radius_min=0.5) 
    
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

    # Center the entire component after all placements
    c.center = (0,0)

    return c

if __name__ == "__main__":
    device = my_device()
    device.write_gds("complex_waveguide.gds")
    # To view the GDS file, uncomment the line below and ensure you have a GDS viewer installed
    # device.show()