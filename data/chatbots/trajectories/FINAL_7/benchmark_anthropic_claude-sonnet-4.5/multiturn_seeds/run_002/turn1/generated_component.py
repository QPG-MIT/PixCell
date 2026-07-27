import gdsfactory as gf

@gf.cell
def chain_link_device():
    """
    Creates a chain-link shaped device with an elliptical outer ring
    and two horizontal bars with rectangular windows.
    """
    c = gf.Component()
    
    # Dimensions based on footprint constraint [3.0, 5.5]
    total_width = 5.5
    total_height = 3.0
    
    # Outer ellipse parameters
    outer_rx = total_width / 2  # 2.75
    outer_ry = total_height / 2  # 1.5
    
    # Inner ellipse (to create ring)
    ring_thickness = 0.38
    inner_rx = outer_rx - ring_thickness
    inner_ry = outer_ry - ring_thickness
    
    # Create outer and inner ellipses
    outer_ellipse = gf.components.ellipse(radii=(outer_rx, outer_ry), layer=(1, 0))
    inner_ellipse = gf.components.ellipse(radii=(inner_rx, inner_ry), layer=(1, 0))
    
    # Create the ring using boolean NOT
    ring = gf.boolean(outer_ellipse, inner_ellipse, operation="not", layer=(1, 0))
    
    # Bar parameters
    bar_height = 0.5
    bar_width = 2.2
    window_width = 0.6
    window_height = 0.25
    gap_between_windows = 0.25
    
    # Position of bars from center
    bar_offset = 0.38
    
    # X offset for windows
    x_offset = (window_width + gap_between_windows) / 2
    
    # Helper function to create positioned rectangles
    def positioned_rect(size, position):
        """Create a rectangle component at a specific position"""
        temp_c = gf.Component()
        rect_ref = temp_c << gf.components.rectangle(size=size, layer=(1, 0), centered=True)
        rect_ref.move(position)
        return temp_c
    
    # === TOP BAR ===
    top_bar_rect = positioned_rect((bar_width, bar_height), (0, bar_offset))
    win1_top = positioned_rect((window_width, window_height), (-x_offset, bar_offset))
    win2_top = positioned_rect((window_width, window_height), (x_offset, bar_offset))
    
    # Create top bar with windows cut out
    top_bar = gf.boolean(top_bar_rect, win1_top, operation="not", layer=(1, 0))
    top_bar = gf.boolean(top_bar, win2_top, operation="not", layer=(1, 0))
    
    # === BOTTOM BAR ===
    bottom_bar_rect = positioned_rect((bar_width, bar_height), (0, -bar_offset))
    win1_bottom = positioned_rect((window_width, window_height), (-x_offset, -bar_offset))
    win2_bottom = positioned_rect((window_width, window_height), (x_offset, -bar_offset))
    
    # Create bottom bar with windows cut out
    bottom_bar = gf.boolean(bottom_bar_rect, win1_bottom, operation="not", layer=(1, 0))
    bottom_bar = gf.boolean(bottom_bar, win2_bottom, operation="not", layer=(1, 0))
    
    # === COMBINE ALL PARTS ===
    final_device = gf.boolean(ring, top_bar, operation="or", layer=(1, 0))
    final_device = gf.boolean(final_device, bottom_bar, operation="or", layer=(1, 0))
    
    c << final_device
    
    return c

# Create and save the device
if __name__ == "__main__":
    device = chain_link_device()
    device.write_gds("chain_link_device.gds")
    print("Chain link device created successfully!")