import gdsfactory as gf
import numpy as np

def create_photonic_splitter() -> gf.Component:
    """
    Creates a 1x2 photonic splitter matching the provided silhouette.
    Footprint: 40.0um x 1.7um
    Layer: (1, 0)
    """
    c = gf.Component("photonic_splitter")
    layer = (1, 0)

    # Global dimensions
    L = 40.0
    H = 1.7
    
    # Specific geometry parameters derived from image analysis
    x_input_end = 25.0      # Point where the central taper ends
    x_side_start = 3.1      # Offset where side waveguides begin
    x_bend_start = 24.0     # Start of the S-bend divergence
    x_bend_end = 36.0       # End of the S-bend divergence
    
    w_input = 0.6           # Initial width of the central input
    w_output = 0.5          # Final width of the two output branches
    w_side_init = 0.1       # Initial tip width of the side branches
    gap_coupling = 0.05     # Gap between central and side waveguides
    
    # 1. Central Input Waveguide
    # Tapers linearly from w_input to a sharp tip
    pts_center = [
        (0, w_input/2),
        (x_input_end, 0.005),
        (x_input_end, -0.005),
        (0, -w_input/2)
    ]
    c.add_polygon(pts_center, layer=layer)

    # 2. Side Waveguides (Upper and Lower)
    x_coords = []
    y_upper_in = []
    y_upper_out = []
    
    # a. Coupling region: waveguides follow the central taper
    num_pts_coupling = 50
    xs_c = np.linspace(x_side_start, x_bend_start, num_pts_coupling)
    for x in xs_c:
        x_coords.append(x)
        # Calculate width of the central waveguide at this x to maintain gap
        w_c = w_input * (1.0 - x / x_input_end) if x < x_input_end else 0.0
        y_in = max(0.005, w_c / 2.0) + gap_coupling
        # Side waveguide tapers up from its initial tip to the output width
        w_s = w_side_init + (w_output - w_side_init) * (x - x_side_start) / (x_bend_start - x_side_start)
        y_upper_in.append(y_in)
        y_upper_out.append(y_in + w_s)
        
    # b. S-bend region: waveguides diverge to final separation
    num_pts_bend = 50
    xs_b = np.linspace(x_bend_start, x_bend_end, num_pts_bend)[1:] # Avoid duplicate start point
    y_center_start = (y_upper_in[-1] + y_upper_out[-1]) / 2.0
    y_center_end = 0.6  # Final center y-pos; total height H=1.7 implies outer edge at 0.6+0.25=0.85
    
    for x in xs_b:
        x_coords.append(x)
        t = (x - x_bend_start) / (x_bend_end - x_bend_start)
        # S-curve function (smooth transition)
        y_mid = y_center_start + (y_center_end - y_center_start) * (3*t**2 - 2*t**3)
        y_upper_in.append(y_mid - w_output/2.0)
        y_upper_out.append(y_mid + w_output/2.0)
        
    # c. Final straight section to reach length L
    x_coords.append(L)
    y_upper_in.append(y_center_end - w_output/2.0)
    y_upper_out.append(y_center_end + w_output/2.0)
    
    # Define the polygon for the upper side waveguide
    pts_upper = []
    # Outer edge: left to right
    for i in range(len(x_coords)):
        pts_upper.append((x_coords[i], y_upper_out[i]))
    # Inner edge: right to left
    for i in range(len(x_coords)-1, -1, -1):
        pts_upper.append((x_coords[i], y_upper_in[i]))
    
    c.add_polygon(pts_upper, layer=layer)
    
    # Mirror the upper waveguide to create the lower arm
    pts_lower = [(p[0], -p[1]) for p in pts_upper]
    c.add_polygon(pts_lower, layer=layer)
    
    return c

if __name__ == "__main__":
    # Create the component
    component = create_photonic_splitter()
    
    # Save as GDS
    component.write_gds("component.gds")
    print("Component saved to component.gds")
