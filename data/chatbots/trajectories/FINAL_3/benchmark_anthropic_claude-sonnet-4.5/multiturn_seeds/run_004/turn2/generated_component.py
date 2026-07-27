import gdsfactory as gf

@gf.cell
def device():
    """
    Creates a bracket-shaped structure with two parallel horizontal waveguides
    connected by curved sections on the right side with a vertical gap.
    Footprint: approximately 120 x 4 um
    """
    c = gf.Component()
    
    # Parameters
    wg_width = 0.5  # Waveguide width in um
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))
    
    # Dimensions
    straight_length = 90  # Length of horizontal sections
    bend_radius = 1.75  # Radius of the curves
    vertical_gap = 1.0  # Gap between top and bottom in the middle
    separation = vertical_gap + 2 * bend_radius + wg_width  # Total vertical separation
    
    # Top path: straight right, then curve down 90°, then short straight down
    top_path = gf.Path()
    top_path += gf.path.straight(length=straight_length)
    top_path += gf.path.arc(radius=bend_radius, angle=-90)
    top_path += gf.path.straight(length=vertical_gap/2)
    
    top_structure = c << gf.path.extrude(top_path, cross_section=xs)
    top_structure.movey(separation/2)
    
    # Bottom path: straight right, then curve up 90°, then short straight up
    bottom_path = gf.Path()
    bottom_path += gf.path.straight(length=straight_length)
    bottom_path += gf.path.arc(radius=bend_radius, angle=90)
    bottom_path += gf.path.straight(length=vertical_gap/2)
    
    bottom_structure = c << gf.path.extrude(bottom_path, cross_section=xs)
    bottom_structure.movey(-separation/2)
    
    return c

# Create the device and save
if __name__ == "__main__":
    device_component = device()
    device_component.write_gds("device.gds")
    print("GDS file 'device.gds' has been generated successfully!")
    print(f"Device size: {device_component.bbox}")