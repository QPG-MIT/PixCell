import gdsfactory as gf

@gf.cell
def device():
    """
    Creates a device with two waveguides that converge in the middle
    and diverge at the edges, matching the footprint constraint of 120x4 µm.
    """
    c = gf.Component()
    
    # Define cross-section with appropriate width
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # Parameters based on footprint [120, 4] µm
    total_length = 120.0
    outer_offset = 1.85   # Vertical position at edges (±1.85 µm for ~3.7 µm separation)
    inner_offset = 0.5    # Vertical position in middle (±0.5 µm for ~1 µm separation)
    transition_start = 15.0   # Where transition begins (earlier)
    transition_end = 105.0    # Where return transition begins (later)
    bend_radius = 15.0    # Larger radius for smoother bends
    
    # Top waveguide path - starts high, curves down, stays low, curves back up
    points_top = [
        (0, outer_offset),
        (transition_start, inner_offset),
        (transition_end, inner_offset),
        (total_length, outer_offset)
    ]
    
    path_top = gf.path.smooth(points_top, radius=bend_radius)
    wg_top = gf.path.extrude(path_top, cross_section=xs)
    c.add_ref(wg_top)
    
    # Bottom waveguide path - starts low, curves up, stays high, curves back down
    points_bottom = [
        (0, -outer_offset),
        (transition_start, -inner_offset),
        (transition_end, -inner_offset),
        (total_length, -outer_offset)
    ]
    
    path_bottom = gf.path.smooth(points_bottom, radius=bend_radius)
    wg_bottom = gf.path.extrude(path_bottom, cross_section=xs)
    c.add_ref(wg_bottom)
    
    return c

# Create and save the device
if __name__ == "__main__":
    device = device()
    device.show()  # Optional: display in viewer
    device.write_gds("device.gds")
    print("Device created successfully!")
    print(f"Bounding box: {device.bbox}")