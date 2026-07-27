import gdsfactory as gf

@gf.cell
def adiabatic_coupler_recreation():
    """
    Recreates the symmetric coupler with global smoothness.
    Uses 'gf.path.smooth' to create a single continuous curve for each arm,
    preventing any kinks at the center point.
    """
    c = gf.Component("smooth_adiabatic_coupler")
    
    # 1. Design Parameters (Matched to 18x3 um footprint)
    length = 18.0
    width = 0.8      # Increased width for better visual match to the original
    center_gap = 0.4 # Visible gap at the pinch point
    
    # Vertical calculations (centers of the waveguides)
    # At the ends: edge at 1.5 -> center at 1.5 - (0.8/2) = 1.1
    y_outer = 1.1 
    # At the center: gap/2 + width/2 = 0.2 + 0.4 = 0.6
    y_inner = 0.6
    
    # Define the cross-section
    xs = gf.cross_section.cross_section(width=width, layer=(1, 0))
    
    # 2. Define Waypoints for Path Creation
    # We use 5 waypoints to ensure:
    # - Perfectly horizontal ports (points 1-2 and 4-5 have same Y)
    # - A symmetric smooth dip in the center (point 3)
    points_top = [
        (0, y_outer),
        (4.0, y_outer),   # Ensures horizontal slope at port
        (9.0, y_inner),   # The smooth 'pinch' point
        (14.0, y_outer),  # Ensures horizontal slope at port
        (18.0, y_outer)
    ]
    
    # 3. Generate and Extrude Paths
    # 'gf.path.smooth' creates one continuous path through all guide points.
    path_top = gf.path.smooth(points=points_top, radius=6.0)
    
    # Mirror the waypoints for the bottom arm
    points_bot = [(x, -y) for x, y in points_top]
    path_bot = gf.path.smooth(points=points_bot, radius=6.0)
    
    # Extrude paths into geometry
    top_arm = c << gf.path.extrude(path_top, cross_section=xs)
    bot_arm = c << gf.path.extrude(path_bot, cross_section=xs)
    
    # 4. Add Ports for external connectivity
    c.add_port("o1", port=top_arm.ports["o1"])
    c.add_port("o2", port=top_arm.ports["o2"])
    c.add_port("o3", port=bot_arm.ports["o1"])
    c.add_port("o4", port=bot_arm.ports["o2"])

    return c

if __name__ == "__main__":
    # Initialize the component
    device = adiabatic_coupler_recreation()
    
    # Explicitly write the GDS file
    device.write_gds("smooth_coupler.gds")
    
    print("GDS file 'smooth_coupler.gds' has been generated.")
    print(f"Final Dimensions: {device.size_info.width:.1f}um x {device.size_info.height:.1f}um")