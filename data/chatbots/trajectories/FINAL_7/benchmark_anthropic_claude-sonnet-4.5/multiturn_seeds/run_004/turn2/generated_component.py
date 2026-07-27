import gdsfactory as gf

@gf.cell
def chain_link_device(
    width: float = 5.5,
    height: float = 3.0,
    ring_thickness: float = 0.35,
    bar_height: float = 0.25,
    bar_spacing: float = 0.25,
    window_width: float = 0.65,
    window_height: float = 0.25,
    window_offset: float = 1.2,
    layer = (1, 0)
):
    """
    Creates a chain-link device with elliptical ring and three horizontal bars.
    
    Args:
        width: Device width in um
        height: Device height in um
        ring_thickness: Thickness of outer elliptical ring
        bar_height: Height (thickness) of horizontal bars
        bar_spacing: Vertical spacing between bars
        window_width: Width of rectangular windows/cutouts in bars
        window_height: Height of rectangular windows
        window_offset: Distance from center to window center
        layer: GDS layer
    """
    c = gf.Component()
    
    # Create outer ellipse
    outer_ellipse = gf.components.ellipse(
        radii=(width/2, height/2),
        layer=layer
    )
    
    # Create inner ellipse for ring
    inner_ellipse = gf.components.ellipse(
        radii=(width/2 - ring_thickness, height/2 - ring_thickness),
        layer=layer
    )
    
    # Create ring by boolean subtraction
    ring = gf.boolean(outer_ellipse, inner_ellipse, operation="not", layer=layer)
    ring_comp = gf.Component()
    ring_comp << ring
    
    # Calculate bar positions
    bar_length = width * 0.75  # Bars span about 75% of width
    top_bar_y = bar_spacing + bar_height/2
    middle_bar_y = 0
    bottom_bar_y = -(bar_spacing + bar_height/2)
    
    # Create TOP bar with cutouts
    top_bar = gf.components.rectangle(
        size=(bar_length, bar_height),
        layer=layer,
        centered=True
    )
    top_bar_comp = gf.Component()
    ref = top_bar_comp << top_bar
    ref.movey(top_bar_y)
    
    # Create left window cutout for top bar
    window_left_top = gf.components.rectangle(
        size=(window_width, window_height),
        layer=layer,
        centered=True
    )
    win_left_top_comp = gf.Component()
    ref = win_left_top_comp << window_left_top
    ref.move((-window_offset, top_bar_y))
    
    # Create right window cutout for top bar
    window_right_top = gf.components.rectangle(
        size=(window_width, window_height),
        layer=layer,
        centered=True
    )
    win_right_top_comp = gf.Component()
    ref = win_right_top_comp << window_right_top
    ref.move((window_offset, top_bar_y))
    
    # Subtract windows from top bar
    top_bar_cut1 = gf.boolean(top_bar_comp, win_left_top_comp, operation="not", layer=layer)
    top_bar_final = gf.boolean(top_bar_cut1, win_right_top_comp, operation="not", layer=layer)
    
    # Create MIDDLE bar (solid, no cutouts)
    middle_bar = gf.components.rectangle(
        size=(bar_length, bar_height),
        layer=layer,
        centered=True
    )
    middle_bar_comp = gf.Component()
    ref = middle_bar_comp << middle_bar
    ref.movey(middle_bar_y)
    
    # Create BOTTOM bar with cutouts
    bottom_bar = gf.components.rectangle(
        size=(bar_length, bar_height),
        layer=layer,
        centered=True
    )
    bottom_bar_comp = gf.Component()
    ref = bottom_bar_comp << bottom_bar
    ref.movey(bottom_bar_y)
    
    # Create left window cutout for bottom bar
    window_left_bottom = gf.components.rectangle(
        size=(window_width, window_height),
        layer=layer,
        centered=True
    )
    win_left_bot_comp = gf.Component()
    ref = win_left_bot_comp << window_left_bottom
    ref.move((-window_offset, bottom_bar_y))
    
    # Create right window cutout for bottom bar
    window_right_bottom = gf.components.rectangle(
        size=(window_width, window_height),
        layer=layer,
        centered=True
    )
    win_right_bot_comp = gf.Component()
    ref = win_right_bot_comp << window_right_bottom
    ref.move((window_offset, bottom_bar_y))
    
    # Subtract windows from bottom bar
    bottom_bar_cut1 = gf.boolean(bottom_bar_comp, win_left_bot_comp, operation="not", layer=layer)
    bottom_bar_final = gf.boolean(bottom_bar_cut1, win_right_bot_comp, operation="not", layer=layer)
    
    # Combine all bars
    bars_step1 = gf.boolean(top_bar_final, middle_bar_comp, operation="or", layer=layer)
    bars_combined = gf.boolean(bars_step1, bottom_bar_final, operation="or", layer=layer)
    
    # Combine ring with bars
    final_device = gf.boolean(ring_comp, bars_combined, operation="or", layer=layer)
    
    # Add to component
    c << final_device
    
    return c


# Create the device and save
if __name__ == "__main__":
    device = chain_link_device()
    device.show()  # Optional: display in viewer
    device.write_gds("chain_link_device.gds")
    print("GDS file 'chain_link_device.gds' created successfully!")