import gdsfactory as gf

@gf.cell
def symmetric_coupler_refined():
    """
    Recreates the symmetric coupler geometry with 120um x 4um footprint.
    Uses Path Extrusion to ensure correct topology and smooth adiabatic transitions.
    """
    c = gf.Component("refined_coupler")

    # 1. Design Parameters based on footprint (120um x 4um)
    width = 0.5   # Waveguide width
    gap = 0.2     # Coupling gap
    L_total = 120
    H_total = 4
    
    # Calculated Y-coordinates for path centers
    # Inner (coupler) region: centered at +/- (gap/2 + width/2)
    y_inner = (gap / 2) + (width / 2)  # 0.35 um
    # Outer (ports) region: flush with the 4um footprint boundary
    y_outer = (H_total / 2) - (width / 2) # 1.75 um

    # 2. Define the Cross-Section
    xs = gf.cross_section.cross_section(width=width, layer=(1, 0))

    # 3. Define Path Trajectories (X-coordinates symmetric around 0)
    # x: [-60, -50] = straight, [-50, -25] = transition, [-25, 25] = coupler
    x_points = [-60, -50, -25, 25, 50, 60]
    
    # Top Waveguide Points
    points_top = [
        (x_points[0], y_outer), 
        (x_points[1], y_outer), 
        (x_points[2], y_inner), 
        (x_points[3], y_inner), 
        (x_points[4], y_outer), 
        (x_points[5], y_outer)
    ]
    
    # Bottom Waveguide Points (Mirrored Y)
    points_bot = [(x, -y) for x, y in points_top]

    # 4. Create and Smooth Paths
    # gf.path.smooth automatically inserts adiabatic bends between waypoints
    path_top = gf.path.smooth(points=points_top, radius=15.0)
    path_bot = gf.path.smooth(points=points_bot, radius=15.0)

    # 5. Extrude and Add to Component
    c << gf.path.extrude(path_top, cross_section=xs)
    c << gf.path.extrude(path_bot, cross_section=xs)

    # 6. Add Ports for connectivity
    c.add_port("o1", center=(-60, -y_outer), width=width, orientation=180, layer=(1,0))
    c.add_port("o2", center=(-60, y_outer), width=width, orientation=180, layer=(1,0))
    c.add_port("o3", center=(60, y_outer), width=width, orientation=0, layer=(1,0))
    c.add_port("o4", center=(60, -y_outer), width=width, orientation=0, layer=(1,0))

    return c

if __name__ == "__main__":
    device = symmetric_coupler_refined()
    device.show()
    
    # Final check: Footprint should be exactly 120 x 4
    print(f"Device Bounding Box: {device.size_info.width} x {device.size_info.height} um")
    device.write_gds("refined_coupler.gds")