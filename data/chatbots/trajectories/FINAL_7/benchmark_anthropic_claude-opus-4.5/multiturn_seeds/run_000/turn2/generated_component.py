import gdsfactory as gf
import numpy as np

@gf.cell
def create_stadium(width: float, height: float, layer: tuple = (1, 0)) -> gf.Component:
    """Create a stadium (pill) shape using polygon points."""
    c = gf.Component()
    
    r = height / 2
    rect_len = max(0, width - height)
    
    # Create stadium using points
    npoints = 64
    angles_left = np.linspace(np.pi/2, 3*np.pi/2, npoints//2)
    angles_right = np.linspace(-np.pi/2, np.pi/2, npoints//2)
    
    # Left semicircle
    left_x = -rect_len/2
    left_points = [(left_x + r * np.cos(a), r * np.sin(a)) for a in angles_left]
    
    # Right semicircle
    right_x = rect_len/2
    right_points = [(right_x + r * np.cos(a), r * np.sin(a)) for a in angles_right]
    
    # Combine all points
    all_points = left_points + right_points
    
    c.add_polygon(all_points, layer=layer)
    return c


@gf.cell
def create_bar_with_windows(
    width: float,
    height: float,
    num_windows: int,
    win_w: float,
    win_h: float,
    layer: tuple = (1, 0)
) -> gf.Component:
    """Create a stadium-shaped bar with rectangular window cutouts."""
    c = gf.Component()
    
    # Create the solid bar
    bar = create_stadium(width, height, layer)
    
    if num_windows == 0:
        c << bar
        return c
    
    # Create windows component
    windows = gf.Component()
    
    # Calculate window positions in the straight section
    usable_width = width - height  # exclude rounded ends
    total_win_width = num_windows * win_w
    spacing = (usable_width - total_win_width) / (num_windows + 1)
    
    x_start = -usable_width/2 + spacing + win_w/2
    for i in range(num_windows):
        x_pos = x_start + i * (win_w + spacing)
        win_points = [
            (x_pos - win_w/2, -win_h/2),
            (x_pos + win_w/2, -win_h/2),
            (x_pos + win_w/2, win_h/2),
            (x_pos - win_w/2, win_h/2),
        ]
        windows.add_polygon(win_points, layer=layer)
    
    # Boolean subtraction
    result = gf.boolean(bar, windows, operation="not", layer=layer)
    if result is not None:
        c << result
    else:
        c << bar
    
    return c


@gf.cell
def chain_link_device() -> gf.Component:
    """
    Chain link icon: outer stadium ring with two inner bars containing rectangular windows.
    Footprint approximately 5.5 x 3.0 um (width x height).
    """
    c = gf.Component()
    layer = (1, 0)
    
    # Main dimensions - more compact to fit properly
    outer_width = 5.0
    outer_height = 2.5
    border_thickness = 0.25
    
    # Bar parameters - bars must fit inside the ring
    inner_width = outer_width - 2 * border_thickness
    inner_height = outer_height - 2 * border_thickness
    
    # Bars should span most of the inner width but leave some margin
    bar_width = inner_width - 0.3
    bar_height = 0.35
    bar_y_offset = 0.42
    
    # Window parameters
    window_width = 0.45
    window_height = 0.18
    
    # === Create outer stadium ring ===
    outer_stadium = create_stadium(outer_width, outer_height, layer)
    inner_stadium = create_stadium(inner_width, inner_height, layer)
    
    outer_ring = gf.boolean(outer_stadium, inner_stadium, operation="not", layer=layer)
    if outer_ring is not None:
        c << outer_ring
    
    # === Create top bar with 3 windows ===
    top_bar = create_bar_with_windows(
        width=bar_width,
        height=bar_height,
        num_windows=3,
        win_w=window_width,
        win_h=window_height,
        layer=layer
    )
    top_ref = c << top_bar
    top_ref.dmove((0, bar_y_offset))
    
    # === Create bottom bar with 2 windows ===
    bottom_bar = create_bar_with_windows(
        width=bar_width,
        height=bar_height,
        num_windows=2,
        win_w=window_width,
        win_h=window_height,
        layer=layer
    )
    bottom_ref = c << bottom_bar
    bottom_ref.dmove((0, -bar_y_offset))
    
    return c


# Create and save the device
if __name__ == "__main__":
    device = chain_link_device()
    device.write_gds("chain_link_device.gds")
    print(f"Device size: {device.dxsize:.2f} x {device.dysize:.2f} um")