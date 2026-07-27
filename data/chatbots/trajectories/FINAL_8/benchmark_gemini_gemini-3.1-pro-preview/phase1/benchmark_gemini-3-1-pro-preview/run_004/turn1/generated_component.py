import gdsfactory as gf

@gf.cell
def mode_converter_coupler():
    """
    Creates the symmetric multi-waveguide directional coupler structure.
    Designed mathematically to hit the exact [120.0, 4.0] footprint bounding box.
    """
    c = gf.Component("mode_converter_coupler")

    # --- Global Footprint & Grid Parameters ---
    L = 120.0
    layer = (1, 0)
    
    # Base unit 'u' derived to perfectly fit the 4.0um total height
    u = 0.08  

    # X-coordinates for the routing path waypoints
    # Flares transition from straight parallel middle out to separated parallel ends
    x_end_left = -L / 2
    x_flare_left = -45.0
    x_straight_left = -25.0
    x_straight_right = 25.0
    x_flare_right = 45.0
    x_end_right = L / 2

    # --- 1. Center Straight Waveguides ---
    # 5 uniform straight lines symmetrically placed around y=0
    center_offsets = [0, 2*u, -2*u, 4*u, -4*u]

    for offset in center_offsets:
        # Create pure straight paths for the center elements
        p_center = gf.Path([(x_end_left, offset), (x_end_right, offset)])
        xs = gf.cross_section.cross_section(width=u, layer=layer)
        c << gf.path.extrude(p_center, cross_section=xs)

    # --- 2. Upper and Lower Bending Blocks ---
    # Base reference Y offsets (bottom edge of the upper block)
    # 4.5u (center half-width) + 1.0u (gap spacing) = 5.5u
    y_base_straight = 5.5 * u  
    
    # Outer ports are mathematically offset to reach exactly 2.0um on the extreme bounding box edge
    y_base_end = y_base_straight + 0.28  

    # Define the composition of lines in the upper block 
    # (Distance from block's inner edge, line width)
    block_lines = [
        {'local_offset': 1.5*u,  'width': 3*u}, # Thickest lower boundary
        {'local_offset': 4.5*u,  'width': u},   # Thin internal line 1
        {'local_offset': 6.5*u,  'width': u},   # Thin internal line 2
        {'local_offset': 8.5*u,  'width': u},   # Thin internal line 3
        {'local_offset': 10.5*u, 'width': u},   # Thin internal line 4
        {'local_offset': 14.0*u, 'width': 4*u}, # Thick outer boundary
    ]

    def add_bent_parallel_line(y_straight, y_end, width):
        """Helper function to extrude a smoothed bend path ensuring orthogonal bounding edges."""
        pts = [
            (x_end_left, y_end),             # Enforce horizontal start
            (x_flare_left, y_end),
            (x_straight_left, y_straight),   # Bend into closely packed center
            (x_straight_right, y_straight),
            (x_flare_right, y_end),          # Flare out
            (x_end_right, y_end)             # Enforce horizontal end
        ]
        # Smooth path automatically transitions lines using optimal curving
        p = gf.path.smooth(pts, radius=10.0)
        xs = gf.cross_section.cross_section(width=width, layer=layer)
        c << gf.path.extrude(p, cross_section=xs)

    # Add Upper block lines
    for line in block_lines:
        y_straight = y_base_straight + line['local_offset']
        y_end = y_base_end + line['local_offset']
        add_bent_parallel_line(y_straight, y_end, line['width'])

    # Add Lower block lines (Mirrored exactly to the negative Y-axis)
    for line in block_lines:
        y_straight = -(y_base_straight + line['local_offset'])
        y_end = -(y_base_end + line['local_offset'])
        add_bent_parallel_line(y_straight, y_end, line['width'])

    return c


if __name__ == "__main__":
    # Generate the component and save to a .gds file
    c = mode_converter_coupler()
    c.write_gds("mode_converter_coupler.gds")