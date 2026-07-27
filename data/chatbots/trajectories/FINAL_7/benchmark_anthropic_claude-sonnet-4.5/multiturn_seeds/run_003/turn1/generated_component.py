import gdsfactory as gf

@gf.cell
def chain_link_device():
    """Creates a chain-link structure within an elliptical border."""
    c = gf.Component()
    
    # Dimensions based on footprint [3.0, 5.5] um (height, width)
    total_width = 5.5
    total_height = 3.0
    
    # Create outer ellipse ring
    ring_thickness = 0.35
    outer_ellipse = gf.components.ellipse(
        radii=(total_width/2, total_height/2), 
        layer=(1, 0)
    )
    inner_ellipse = gf.components.ellipse(
        radii=(total_width/2 - ring_thickness, total_height/2 - ring_thickness),
        layer=(1, 0)
    )
    ring = gf.boolean(outer_ellipse, inner_ellipse, operation="not", layer=(1, 0))
    c << ring
    
    # Internal structure parameters
    bar_length = 3.8
    bar_thickness = 0.4
    bar_offset = 0.53
    
    window_width = 1.15
    window_height = 0.28
    window_x_offset = 1.0
    
    connector_width = 0.55
    connector_height = 2 * bar_offset
    connector_x_offset = 0.35
    
    # Create top horizontal bar with windows
    # Use a temporary component to position windows
    temp_top = gf.Component()
    
    window_left = gf.components.rectangle(
        size=(window_width, window_height),
        layer=(1, 0),
        centered=True
    )
    wl_ref = temp_top << window_left
    wl_ref.movex(-window_x_offset)
    
    window_right = gf.components.rectangle(
        size=(window_width, window_height),
        layer=(1, 0),
        centered=True
    )
    wr_ref = temp_top << window_right
    wr_ref.movex(window_x_offset)
    
    # Flatten to merge into single component
    temp_top_flat = temp_top.flatten()
    
    # Now create the bar and subtract windows
    top_bar_solid = gf.components.rectangle(
        size=(bar_length, bar_thickness),
        layer=(1, 0),
        centered=True
    )
    
    # Subtract windows from bar
    top_bar_with_holes = gf.boolean(top_bar_solid, temp_top_flat, operation="not", layer=(1, 0))
    top_bar_ref = c << top_bar_with_holes
    top_bar_ref.movey(bar_offset)
    
    # Create bottom horizontal bar with windows
    temp_bottom = gf.Component()
    
    window_left2 = gf.components.rectangle(
        size=(window_width, window_height),
        layer=(1, 0),
        centered=True
    )
    wl2_ref = temp_bottom << window_left2
    wl2_ref.movex(-window_x_offset)
    
    window_right2 = gf.components.rectangle(
        size=(window_width, window_height),
        layer=(1, 0),
        centered=True
    )
    wr2_ref = temp_bottom << window_right2
    wr2_ref.movex(window_x_offset)
    
    # Flatten to merge
    temp_bottom_flat = temp_bottom.flatten()
    
    bottom_bar_solid = gf.components.rectangle(
        size=(bar_length, bar_thickness),
        layer=(1, 0),
        centered=True
    )
    
    # Subtract windows from bar
    bottom_bar_with_holes = gf.boolean(bottom_bar_solid, temp_bottom_flat, operation="not", layer=(1, 0))
    bottom_bar_ref = c << bottom_bar_with_holes
    bottom_bar_ref.movey(-bar_offset)
    
    # Add vertical connectors between top and bottom bars
    left_connector = c << gf.components.rectangle(
        size=(connector_width, connector_height),
        layer=(1, 0),
        centered=True
    )
    left_connector.movex(-connector_x_offset)
    
    right_connector = c << gf.components.rectangle(
        size=(connector_width, connector_height),
        layer=(1, 0),
        centered=True
    )
    right_connector.movex(connector_x_offset)
    
    return c

# Create the device and save
device = chain_link_device()
device.write_gds("chain_link_device.gds")
print("GDS file 'chain_link_device.gds' created successfully!")

# Optional: display the device
device.show()