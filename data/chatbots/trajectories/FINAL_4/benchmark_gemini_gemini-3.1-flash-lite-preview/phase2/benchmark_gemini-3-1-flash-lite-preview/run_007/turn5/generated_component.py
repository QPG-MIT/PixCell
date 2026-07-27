import gdsfactory as gf

@gf.cell
def fused_coupler():
    """
    Creates a fused waveguide coupler by constructing two smooth S-paths
    using gf.path.smooth and merging them with a boolean OR.
    """
    c = gf.Component()
    
    # Define cross-section
    # width=0.8 gives a radius of 0.4 for each waveguide.
    xs = gf.cross_section.cross_section(width=0.8, layer=(1, 0))
    
    # Define two smooth paths using waypoints.
    # We use y=0.1 and y=-0.1 as the centers.
    # Path 1: (0, 0.1) -> (9, 0.1) -> (9, -0.1) -> (18, -0.1)
    # Path 2: (0, -0.1) -> (9, -0.1) -> (9, 0.1) -> (18, 0.1)
    # The vertical distance between turns is 0.2. A radius of 0.08 
    # fits comfortably within this segment.
    p1 = gf.path.smooth(points=[(0, 0.1), (9, 0.1), (9, -0.1), (18, -0.1)], radius=0.08)
    p2 = gf.path.smooth(points=[(0, -0.1), (9, -0.1), (9, 0.1), (18, 0.1)], radius=0.08)
    
    # Extrude the paths into waveguides
    w1 = gf.path.extrude(p1, cross_section=xs)
    w2 = gf.path.extrude(p2, cross_section=xs)
    
    # Boolean OR operation merges the overlapping waveguides into a single 
    # fused geometry at the center
    merged = gf.boolean(w1, w2, operation="or", layer=(1, 0))
    
    # Add the merged geometry to the main component
    c << merged
    
    return c

# Generate and save
if __name__ == "__main__":
    device = fused_coupler()
    device.write_gds("fused_coupler.gds")