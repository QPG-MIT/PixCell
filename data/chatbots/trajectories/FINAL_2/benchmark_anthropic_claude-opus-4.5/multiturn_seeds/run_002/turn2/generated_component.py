import gdsfactory as gf

@gf.cell
def bottles_in_crate():
    """
    Creates a device shape resembling 4 bottles in a crate/carrier.
    Adjusted proportions to better match target.
    """
    c = gf.Component()
    layer = (1, 0)
    
    # Design parameters - adjusted for better proportions
    box_width = 18.0
    box_height = 5.0
    bottle_neck_height = 7.5  # Much taller bottles
    bottle_top_width = 1.5    # Narrower tops
    bottle_base_width = 4.5   # Bases just touch
    notch_width = 2.0
    notch_height = 1.2
    
    # Four bottle positions - evenly spaced so bases touch
    # Spacing = 4.5 between centers
    bottle_x_positions = [-6.75, -2.25, 2.25, 6.75]
    
    # Create main rectangular crate (bottom portion)
    c.add_polygon([
        (-box_width/2, 0),
        (-box_width/2, box_height),
        (box_width/2, box_height),
        (box_width/2, 0),
    ], layer=layer)
    
    # Create four bottle neck trapezoids (tapered from wide base to narrow top)
    # Bases touch at box_height, creating V-gaps that go to sharp points
    for x in bottle_x_positions:
        c.add_polygon([
            (x - bottle_base_width/2, box_height),              # bottom-left
            (x - bottle_top_width/2, box_height + bottle_neck_height),   # top-left
            (x + bottle_top_width/2, box_height + bottle_neck_height),   # top-right
            (x + bottle_base_width/2, box_height),              # bottom-right
        ], layer=layer)
    
    # Create bottom triangular notch (pointing downward)
    c.add_polygon([
        (-notch_width/2, 0),
        (notch_width/2, 0),
        (0, -notch_height)
    ], layer=layer)
    
    return c


# Generate and save the device
if __name__ == "__main__":
    device = bottles_in_crate()
    device.write_gds("bottles_in_crate.gds")