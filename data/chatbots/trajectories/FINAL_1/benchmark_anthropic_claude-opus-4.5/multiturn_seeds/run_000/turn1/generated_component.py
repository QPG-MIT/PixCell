import gdsfactory as gf

@gf.cell
def waveguide_crossing_coupler():
    """
    Creates a waveguide crossing device with:
    - Two parallel input waveguides on the left
    - Crossing region in the middle
    - Diverging curves on the right with one arm looping back
    """
    c = gf.Component()
    
    # Parameters based on footprint constraint: 40 x 1.7 um
    layer = (1, 0)
    wg_width = 0.35
    
    xs = gf.cross_section.cross_section(width=wg_width, layer=layer)
    
    # Top waveguide path: starts top-left, angles toward center, curves up-right
    top_path_points = [
        (0, 0.55),       # Start top-left
        (10, 0.35),      # Angle toward center
        (20, 0.15),      # Near crossing region
        (30, 0.30),      # Curving up
        (40, 0.50),      # End top-right
    ]
    path_top = gf.path.smooth(points=top_path_points, radius=5)
    wg_top = c << gf.path.extrude(path_top, cross_section=xs)
    
    # Bottom waveguide path: starts bottom-left, angles up toward crossing,
    # then curves down and loops back up toward the top waveguide
    bottom_path_points = [
        (0, -0.55),      # Start bottom-left
        (10, -0.35),     # Angle toward center
        (20, -0.15),     # Near crossing region
        (28, -0.50),     # Curve down
        (34, -0.55),     # Continue curve
        (38, -0.20),     # Start looping back up
        (40, 0.15),      # End curving up toward top arm
    ]
    path_bottom = gf.path.smooth(points=bottom_path_points, radius=4)
    wg_bottom = c << gf.path.extrude(path_bottom, cross_section=xs)
    
    # Add ports for connectivity
    c.add_port("o1", port=wg_top.ports["o1"])
    c.add_port("o2", port=wg_bottom.ports["o1"])
    c.add_port("o3", port=wg_top.ports["o2"])
    c.add_port("o4", port=wg_bottom.ports["o2"])
    
    return c


# Create the device and save
if __name__ == "__main__":
    device = waveguide_crossing_coupler()
    device.show()  # Visualize if KLayout is available
    device.write_gds("waveguide_crossing_coupler.gds")
    print(f"Device size: {device.size}")