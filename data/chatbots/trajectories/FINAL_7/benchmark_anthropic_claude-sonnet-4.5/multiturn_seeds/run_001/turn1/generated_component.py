import gdsfactory as gf

@gf.cell
def chain_link_device():
    c = gf.Component()
    
    # Overall dimensions (width x height)
    width = 5.5
    height = 3.0
    
    # Create outer ellipse ring
    ring_thickness = 0.4
    outer_ellipse = gf.components.ellipse(radii=(width/2, height/2), layer=(1, 0))
    inner_ellipse = gf.components.ellipse(
        radii=(width/2 - ring_thickness, height/2 - ring_thickness), 
        layer=(1, 0)
    )
    ring = gf.boolean(outer_ellipse, inner_ellipse, operation="not", layer=(1, 0))
    ring_ref = c << ring
    ring_ref.move((0, 0))
    
    # Create horizontal link bars with cutouts
    bar_width = 4.4
    bar_height = 0.55
    bar_y_offset = 0.8
    
    # Cutout dimensions
    cutout_width = 0.75
    cutout_height = 0.35
    cutout_spacing = 0.85  # spacing between cutout centers
    
    # Top bar
    top_bar_base = gf.components.rectangle(
        size=(bar_width, bar_height), 
        layer=(1, 0), 
        centered=True
    )
    
    # Create two cutouts
    cutout1 = gf.components.rectangle(
        size=(cutout_width, cutout_height), 
        layer=(1, 0), 
        centered=True
    )
    cutout1_moved = cutout1.copy()
    cutout1_moved.move((-cutout_spacing, 0))
    
    cutout2 = gf.components.rectangle(
        size=(cutout_width, cutout_height), 
        layer=(1, 0), 
        centered=True
    )
    cutout2_moved = cutout2.copy()
    cutout2_moved.move((cutout_spacing, 0))
    
    # Combine cutouts
    combined_cutouts = gf.boolean(cutout1_moved, cutout2_moved, operation="or", layer=(1, 0))
    
    # Subtract cutouts from bar
    top_bar = gf.boolean(top_bar_base, combined_cutouts, operation="not", layer=(1, 0))
    
    # Add top bar
    top_bar_ref = c << top_bar
    top_bar_ref.move((0, bar_y_offset))
    
    # Add bottom bar (copy of top bar)
    bottom_bar_ref = c << top_bar
    bottom_bar_ref.move((0, -bar_y_offset))
    
    return c

# Create and save the device
device = chain_link_device()
device.write_gds("chain_link_device.gds")
print("Chain link device GDS created successfully!")