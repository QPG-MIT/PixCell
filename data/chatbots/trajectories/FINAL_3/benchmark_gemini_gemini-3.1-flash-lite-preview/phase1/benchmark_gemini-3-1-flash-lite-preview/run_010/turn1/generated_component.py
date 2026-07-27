import gdsfactory as gf

@gf.cell
def coupler_device():
    """
    Creates the coupler geometry using path-based parametric functions.
    The paths are defined by waypoints, smoothed with a specific radius 
    to create the S-bend transitions and parallel section.
    """
    c = gf.Component("coupler")
    
    # Define the cross-section
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # 1. Define paths for the top and bottom waveguides
    # We define waypoints based on the desired geometry:
    # (0, 2) -> Start at y=2
    # (40, 0.25) -> Curve inwards to y=0.25
    # (80, 0.25) -> Parallel section at y=0.25
    # (120, 2) -> Curve outwards to y=2
    
    # Top arm path
    path_top = gf.path.smooth(
        points=[(0, 2), (40, 0.25), (80, 0.25), (120, 2)], 
        radius=10
    )
    
    # Bottom arm path (mirrored y-coordinates)
    path_bot = gf.path.smooth(
        points=[(0, -2), (40, -0.25), (80, -0.25), (120, -2)], 
        radius=10
    )
    
    # 2. Extrude the paths into components
    # The 'extrude' function converts the parametric path into geometry
    wg_top = c << gf.path.extrude(path_top, cross_section=xs)
    wg_bot = c << gf.path.extrude(path_bot, cross_section=xs)
    
    return c

# Generate and save the device
if __name__ == "__main__":
    device = coupler_device()
    device.write_gds("coupler.gds")
    
    # Optional: Display the device
    # device.show()