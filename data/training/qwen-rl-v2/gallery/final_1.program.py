import gdsfactory as gf

# Physical footprint: [40.0 um x, 1.7 um y]
# 
# Looking at the image more carefully:
# - There's a thin horizontal bar in the CENTER that extends from left to about 75-80% of the way
# - Above and below it are two thicker strips that start parallel to center
#   but curve outward (away from center) toward the right side
# - The center element is very thin and doesn't extend fully to the right
# - The top and bottom elements curve away and extend to the far right

@gf.cell
def device():
    c = gf.Component()
    
    # Parameters derived from footprint
    total_length = 40.0
    total_height = 1.7
    half_height = total_height / 2
    
    # Center waveguide is very thin
    center_width = 0.1
    
    # Top and bottom elements are thicker
    side_width = 0.35
    
    # Gap parameters
    center_to_side_gap = 0.12
    
    # Layer
    layer = (1, 0)
    
    # Calculate positions
    center_y_offset = center_width / 2
    
    # Top waveguide path: starts at left aligned with above center, 
    # runs straight for most of length, then curves upward away from center
    # Center ends at about 80% of total length
    center_end_x = total_length * 0.78
    
    # Top element
    top_y_start = center_y_offset + center_to_side_gap + center_width/2
    top_y_end_offset = half_height - side_width/2
    
    pts_top = [
        (0, top_y_start),
        (25, top_y_start),
        (30, top_y_start + 0.3),
        (35, top_y_end_offset - 0.1),
        (40, top_y_end_offset),
    ]
    
    path_top = gf.Path(pts_top)
    top_comp = gf.path.extrude(p=path_top, cross_section=gf.cross_section.cross_section(width=side_width, layer=layer))
    ref_top = c << top_comp
    
    # Bottom element (mirror of top)
    pts_bottom = [
        (0, -top_y_start),
        (25, -top_y_start),
        (30, -(top_y_start + 0.3)),
        (35, -(top_y_end_offset - 0.1)),
        (40, -top_y_end_offset),
    ]
    
    path_bottom = gf.Path(pts_bottom)
    bottom_comp = gf.path.extrude(p=path_bottom, cross_section=gf.cross_section.cross_section(width=side_width, layer=layer))
    ref_bottom = c << bottom_comp
    
    # Center waveguide
    center_comp = gf.components.straight(
        length=center_end_x,
        cross_section=gf.cross_section.cross_section(width=center_width, layer=layer)
    )
    ref_center = c << center_comp
    
    # Position center waveguide so its top edge is at center_y_offset
    # The straight component is centered by default or we can adjust
    ref_center.move((0, -center_width/2))
    
    return c

if __name__ == "__main__":
    device().write_gds("device.gds")