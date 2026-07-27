import gdsfactory as gf

@gf.cell
def interlocking_structures():
    c = gf.Component()
    
    # Parameters for 120 x 4 um footprint
    total_width = 120.0
    total_height = 4.0
    
    # Pad dimensions
    pad_width = 12.0
    pad_height = 0.8
    
    # Bar dimensions
    bar_height = 1.2  # Height of each horizontal bar
    gap = 0.4  # Gap between the two bars
    
    # Taper dimensions
    taper_width = 8.0  # Horizontal length of taper
    
    # Calculate positions
    y_top_bar = total_height / 2 - gap / 2
    y_bottom_bar = -total_height / 2 + gap / 2
    
    # Top structure
    # Left pad (top)
    top_left_pad = c << gf.components.rectangle(
        size=(pad_width, pad_height), 
        layer=(1, 0),
        centered=False
    )
    top_left_pad.move((0, y_top_bar))
    
    # Right pad (top)
    top_right_pad = c << gf.components.rectangle(
        size=(pad_width, pad_height),
        layer=(1, 0), 
        centered=False
    )
    top_right_pad.move((total_width - pad_width, y_top_bar))
    
    # Top bar with tapered connections
    points_top = [
        (pad_width, y_top_bar + pad_height),  # End of left pad, top
        (pad_width, y_top_bar),  # End of left pad, bottom
        (pad_width + taper_width, y_top_bar - bar_height),  # After taper
        (total_width - pad_width - taper_width, y_top_bar - bar_height),  # Before right taper
        (total_width - pad_width, y_top_bar),  # Start of right pad
        (total_width - pad_width, y_top_bar + pad_height),  # Top of right pad
        (total_width - pad_width - taper_width, y_top_bar + bar_height),  # After right taper top
        (pad_width + taper_width, y_top_bar + bar_height),  # Before left taper top
    ]
    top_poly = c.add_polygon(points_top, layer=(1, 0))
    
    # Bottom structure (mirrored)
    # Left pad (bottom)
    bottom_left_pad = c << gf.components.rectangle(
        size=(pad_width, pad_height),
        layer=(1, 0),
        centered=False
    )
    bottom_left_pad.move((0, y_bottom_bar - pad_height))
    
    # Right pad (bottom)
    bottom_right_pad = c << gf.components.rectangle(
        size=(pad_width, pad_height),
        layer=(1, 0),
        centered=False
    )
    bottom_right_pad.move((total_width - pad_width, y_bottom_bar - pad_height))
    
    # Bottom bar with tapered connections
    points_bottom = [
        (pad_width, y_bottom_bar - pad_height),  # End of left pad, bottom
        (pad_width, y_bottom_bar),  # End of left pad, top
        (pad_width + taper_width, y_bottom_bar + bar_height),  # After taper
        (total_width - pad_width - taper_width, y_bottom_bar + bar_height),  # Before right taper
        (total_width - pad_width, y_bottom_bar),  # Start of right pad
        (total_width - pad_width, y_bottom_bar - pad_height),  # Bottom of right pad
        (total_width - pad_width - taper_width, y_bottom_bar - bar_height),  # After right taper bottom
        (pad_width + taper_width, y_bottom_bar - bar_height),  # Before left taper bottom
    ]
    bottom_poly = c.add_polygon(points_bottom, layer=(1, 0))
    
    return c

# Create and save the device
device = interlocking_structures()
device.show()  # Optional: display in viewer
device.write_gds("interlocking_structures.gds")