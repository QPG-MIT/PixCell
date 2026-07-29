import gdsfactory as gf

# Declare tunable parameters
footprint_x = 3.0  # micrometers
footprint_y = 5.5  # micrometers

@gf.cell
def device():
    c = gf.Component()
    
    # Overall footprint: 3.0 x 5.5 um
    fw = footprint_x  # x-dimension
    fh = footprint_y  # y-dimension
    
    # Create outer ring
    outer_rect = gf.components.rectangle(
        size=(fw, fh), 
        layer=(1, 0), 
        centered=True
    )
    
    # Inner hole - asymmetric to match the image proportions
    # The ring is thicker horizontally than vertically
    inner_width = fw * 0.72
    inner_height = fh * 0.15
    
    inner_rect = gf.components.rectangle(
        size=(inner_width, inner_height), 
        layer=(1, 0), 
        centered=True
    )
    
    outer_ring = gf.boolean(outer_rect, inner_rect, operation="not", layer=(1, 0))
    c << outer_ring
    
    # Central structure: two parallel horizontal bars
    # Each bar has two rectangular segments connected in the middle
    
    # Bar dimensions
    bar_width = fh * 0.13  # vertical thickness of each horizontal bar
    
    # Width of each rectangular segment
    seg_width = fw * 0.14
    seg_height = bar_width
    
    # Spacing between the two segments
    seg_gap = fw * 0.04
    
    # Vertical offset of bars from center
    # Two bars: one above, one below center
    bar_vertical_offset = fh * 0.10
    
    # Position the left end of the composite structure
    total_segment_span = 2 * seg_width + seg_gap
    left_x_start = -total_segment_span / 2
    
    # Top bar - two rectangles
    top_y = bar_vertical_offset + seg_height / 2  # top of top bar
    
    # Top left rectangle
    tl_rect = gf.components.rectangle(
        size=(seg_width, seg_height), 
        layer=(1, 0), 
        centered=False
    )
    tl_ref = c << tl_rect
    tl_ref.move((left_x_start + seg_width/2, top_y))
    
    # Top right rectangle  
    tr_rect = gf.components.rectangle(
        size=(seg_width, seg_height), 
        layer=(1, 0), 
        centered=False
    )
    tr_ref = c << tr_rect
    tr_ref.move((left_x_start + seg_width + seg_gap + seg_width/2, top_y))
    
    # Bottom bar - two rectangles
    bottom_y = -bar_vertical_offset - seg_height/2
    
    # Bottom left rectangle
    bl_rect = gf.components.rectangle(
        size=(seg_width, seg_height), 
        layer=(1, 0), 
        centered=False
    )
    bl_ref = c << bl_rect
    bl_ref.move((left_x_start + seg_width/2, bottom_y))
    
    # Bottom right rectangle
    br_rect = gf.components.rectangle(
        size=(seg_width, seg_height), 
        layer=(1, 0), 
        centered=False
    )
    br_ref = c << br_rect
    br_ref.move((left_x_start + seg_width + seg_gap + seg_width/2, bottom_y))
    
    # Add connecting bars between the segments (thin vertical connectors)
    connector_width = seg_gap * 0.3
    connector_height = seg_width * 0.6
    
    # Top bar center connector
    top_center_x = left_x_start + seg_width + seg_gap/2
    top_center_y = bar_vertical_offset
    
    top_conn = gf.components.rectangle(
        size=(connector_width, connector_height), 
        layer=(1, 0), 
        centered=True
    )
    top_conn_ref = c << top_conn
    top_conn_ref.move((top_center_x, top_center_y))
    
    # Bottom bar center connector
    bottom_center_x = left_x_start + seg_width + seg_gap/2
    bottom_center_y = -bar_vertical_offset
    
    bottom_conn = gf.components.rectangle(
        size=(connector_width, connector_height), 
        layer=(1, 0), 
        centered=True
    )
    bottom_conn_ref = c << bottom_conn
    bottom_conn_ref.move((bottom_center_x, bottom_center_y))
    
    return c

if __name__ == "__main__":
    device = device()
    device.write_gds("device.gds")