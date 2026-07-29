import gdsfactory as gf

# Device parameters
total_length = 120  # um
total_height = 4    # um
waveguide_width = 0.5 # um
gap = 0.2           # gap between the two waveguides


@gf.cell
def device():
    c = gf.Component()
    
    xs = gf.cross_section.cross_section(width=waveguide_width, layer=(1, 0))
    
    # The device consists of two parallel waveguides that both have S-bends
    # on both ends, going from a narrower section in the middle to wider sections
    # at the ends.
    
    # Based on the image:
    # - Left side: both waveguides curve outward (away from center)
    # - Right side: both waveguides curve outward (away from center)
    # - Center: both waveguides run parallel and closer together
    
    # Actually looking more carefully at the silhouette:
    # The waveguides appear to have S-shaped curves on both ends
    # On the left: top goes down, bottom goes up (approaching each other)
    # In the middle: they run parallel close together
    # On the right: top goes up, bottom goes down (moving apart)
    
    # Let me create two paths for the waveguides
    
    # Define the y-coordinates for the center (close together)
    center_y_top = gap/2 + waveguide_width/2
    center_y_bottom = -gap/2 - waveguide_width/2
    
    # Define the y-coordinates for the wide ends
    end_separation = total_height/2
    end_y_top = end_separation
    end_y_bottom = -end_separation
    
    # Top waveguide path: starts at left end (wide), goes to center, then to right end (wide)
    top_path = gf.path.smooth(
        points=[
            (0, end_y_top),
            (total_length/4, center_y_top),
            (total_length*3/4, center_y_top),
            (total_length, end_y_top)
        ],
        radius=10
    )
    
    # Bottom waveguide path: starts at left end (wide), goes to center, then to right end (wide)
    bottom_path = gf.path.smooth(
        points=[
            (0, end_y_bottom),
            (total_length/4, center_y_bottom),
            (total_length*3/4, center_y_bottom),
            (total_length, end_y_bottom)
        ],
        radius=10
    )
    
    # Extrude both paths
    top_wg = c << gf.path.extrude(p=top_path, cross_section=xs)
    bottom_wg = c << gf.path.extrude(p=bottom_path, cross_section=xs)
    
    return c

if __name__ == "__main__":
    d = device()
    d.write_gds("device.gds")