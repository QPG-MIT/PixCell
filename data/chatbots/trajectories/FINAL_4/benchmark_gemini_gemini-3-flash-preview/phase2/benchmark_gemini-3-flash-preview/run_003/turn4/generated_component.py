import gdsfactory as gf
import numpy as np

@gf.cell
def adiabatic_tapered_coupler():
    """
    Creates an adiabatic coupler with variable width waveguides.
    Matches the 18x3 um footprint exactly.
    The waveguides are wider at the ports and taper down at the coupling region.
    """
    c = gf.Component("adiabatic_tapered_coupler")
    
    # 1. Design Parameters
    length = 18.0
    # Port width and center-to-center distance at ends
    # y_port=1.0 and w_port=1.0 puts the top edge at 1.5 and bottom at -1.5 (Total Height 3.0)
    w_port = 1.0
    y_port = 1.0
    
    # Coupling region width and gap
    w_center = 0.55
    y_center = 0.35  # Results in a gap of 2*y_center - w_center = 0.15um
    
    num_points = 200
    x = np.linspace(0, length, num_points)
    
    # 2. Mathematical Smoothing Function
    def smooth_step(t):
        """
        Raised cosine integral: gives zero derivative and zero curvature 
        at both ends (t=0 and t=1).
        """
        return t - np.sin(2 * np.pi * t) / (2 * np.pi)

    # 3. Calculate Geometry Arrays
    y_top_center = np.zeros_like(x)
    w = np.zeros_like(x)
    
    for i, xi in enumerate(x):
        # We treat the device as two symmetric halves
        if xi <= length/2:
            t = xi / (length/2)
            y_top_center[i] = y_port + (y_center - y_port) * smooth_step(t)
            w[i] = w_port + (w_center - w_port) * smooth_step(t)
        else:
            t = (xi - length/2) / (length/2)
            y_top_center[i] = y_center + (y_port - y_center) * smooth_step(t)
            w[i] = w_center + (w_port - w_center) * smooth_step(t)
            
    # Calculate upper and lower boundaries for the top waveguide
    y_top_upper = y_top_center + w/2
    y_top_lower = y_top_center - w/2
    
    # 4. Construct Polygons
    # Top Arm
    points_top = []
    # Path along top edge (left to right)
    for i in range(num_points):
        points_top.append((x[i], y_top_upper[i]))
    # Path along bottom edge (right to left)
    for i in range(num_points - 1, -1, -1):
        points_top.append((x[i], y_top_lower[i]))
    
    c.add_polygon(points_top, layer=(1, 0))
    
    # Bottom Arm (Mirror of top arm across Y=0)
    points_bottom = [(px, -py) for px, py in points_top]
    c.add_polygon(points_bottom, layer=(1, 0))
    
    # 5. Define Ports for connectivity
    # Using the calculated parameters at x=0 and x=length
    c.add_port(name="o1", center=(0, y_port), width=w_port, orientation=180, layer=(1, 0))
    c.add_port(name="o2", center=(length, y_port), width=w_port, orientation=0, layer=(1, 0))
    c.add_port(name="o3", center=(0, -y_port), width=w_port, orientation=180, layer=(1, 0))
    c.add_port(name="o4", center=(length, -y_port), width=w_port, orientation=0, layer=(1, 0))

    return c

if __name__ == "__main__":
    # Create the component
    device = adiabatic_tapered_coupler()
    
    # Write to GDS
    device.write_gds("tapered_adiabatic_coupler.gds")
    
    # Final check of dimensions
    print(f"Device Name: {device.name}")
    print(f"Footprint: {device.size_info.width:.2f}um x {device.size_info.height:.2f}um")
    print(f"Gap at center: {2*0.35 - 0.55:.3f} um")