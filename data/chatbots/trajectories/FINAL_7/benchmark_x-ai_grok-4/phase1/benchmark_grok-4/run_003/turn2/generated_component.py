import gdsfactory as gf

@gf.cell
def stadium(straight_length, radius, center_y, layer):
    rect_comp = gf.components.rectangle(size=(straight_length, 2 * radius), layer=layer, centered=False)
    rect_comp.move((0, center_y - radius))
    
    left_comp = gf.components.circle(radius=radius, layer=layer)
    left_comp.move((0, center_y))
    
    right_comp = gf.components.circle(radius=radius, layer=layer)
    right_comp.move((straight_length, center_y))
    
    temp = gf.boolean(rect_comp, left_comp, operation="or", layer=layer)
    solid = gf.boolean(temp, right_comp, operation="or", layer=layer)
    return solid

@gf.cell
def device():
    c = gf.Component()

    # Footprint parameters
    height = 3.0
    width = 5.5

    # Parameters (chosen to match image proportions)
    w_ring = 0.5
    center_y = 1.25
    r = 1.25  # Centerline radius
    r_outer = r + w_ring / 2
    r_inner = r - w_ring / 2
    straight_length = width - 2 * r - w_ring

    # Create outer and inner stadium solids
    outer = stadium(straight_length=straight_length, radius=r_outer, center_y=center_y, layer=(1, 0))
    inner = stadium(straight_length=straight_length, radius=r_inner, center_y=center_y, layer=(1, 0))

    # Boolean to create hollow ring
    ring = gf.boolean(outer, inner, operation="not", layer=(1, 0))
    ring_ref = c << ring

    # Internal bars parameters
    w_int = 0.4
    buses_gap = 0.2
    center_distance = buses_gap + w_int
    upper_y = center_y + center_distance / 2
    lower_y = center_y - center_distance / 2

    gap_center = 0.4
    space = -0.3  # Negative to extend into curves for attachment
    segment_length = (straight_length - 2 * space - gap_center) / 2

    center_x = straight_length / 2
    left_start = space
    right_start = center_x + gap_center / 2

    xs_int = gf.cross_section.cross_section(width=w_int, layer=(1, 0))

    # Add internal bar segments
    for y in [upper_y, lower_y]:
        # Left segment
        left_seg = gf.components.straight(length=segment_length, cross_section=xs_int)
        left_ref = c << left_seg
        left_ref.move((left_start, y))

        # Right segment
        right_seg = gf.components.straight(length=segment_length, cross_section=xs_int)
        right_ref = c << right_seg
        right_ref.move((right_start, y))

    return c

# Create and save
dev = device()
dev.write_gds("my_device.gds")