import gdsfactory as gf
import numpy as np

def create_splitter():
    c = gf.Component("splitter_1x2")
    layer = (1, 0)

    # Parameters
    L = 40.0
    H = 1.7
    x_center_end = 25.0
    x_side_start = 3.1
    x_bend_start = 25.0
    x_bend_end = 35.0
    
    w_input = 0.55
    w_output = 0.5
    w_side_min = 0.1
    gap_coupling = 0.06
    
    # 1. Center waveguide (Input)
    # Tapers from w_input to 0 over x_center_end
    pts_center = [
        (0, w_input/2),
        (x_center_end, 0.01),
        (x_center_end, -0.01),
        (0, -w_input/2)
    ]
    c.add_polygon(pts_center, layer=layer)

    # 2. Side Waveguides
    # We'll define the upper one and mirror it.
    
    # Points for the upper side waveguide
    x_side = []
    y_upper_inner = []
    y_upper_outer = []
    
    # a. Coupling region (x_side_start to x_bend_start)
    num_pts_coupling = 50
    x_c = np.linspace(x_side_start, x_bend_start, num_pts_coupling)
    for x in x_c:
        x_side.append(x)
        # Center waveguide width at x
        w_c_x = w_input * (1 - x / x_center_end) if x < x_center_end else 0
        y_in = max(0.01, w_c_x / 2) + gap_coupling
        # Side waveguide width tapers from w_side_min to w_output
        w_s_x = w_side_min + (w_output - w_side_min) * (x - x_side_start) / (x_bend_start - x_side_start)
        y_upper_inner.append(y_in)
        y_upper_outer.append(y_in + w_s_x)
        
    # b. Transition/S-bend region (x_bend_start to x_bend_end)
    num_pts_bend = 50
    x_b = np.linspace(x_bend_start, x_bend_end, num_pts_bend)
    y_center_start = (y_upper_inner[-1] + y_upper_outer[-1]) / 2
    y_center_end = 0.6  # Half of 1.2, giving some gap on right
    # Note: total height 1.7, if w=0.5, top edge is at 0.6+0.25=0.85. Correct.
    
    for x in x_b[1:]: # Skip first to avoid duplicate
        x_side.append(x)
        t = (x - x_bend_start) / (x_bend_end - x_bend_start)
        # S-curve: y = y0 + (y1-y0)*(3t^2 - 2t^3)
        y_mid = y_center_start + (y_center_end - y_center_start) * (3*t**2 - 2*t**3)
        y_upper_inner.append(y_mid - w_output/2)
        y_upper_outer.append(y_mid + w_output/2)
        
    # c. Final straight region (x_bend_end to L)
    x_side.append(L)
    y_upper_inner.append(y_center_end - w_output/2)
    y_upper_outer.append(y_center_end + w_output/2)
    
    # Construct polygon
    pts_upper = []
    # Outer edge: left to right
    for i in range(len(x_side)):
        pts_upper.append((x_side[i], y_upper_outer[i]))
    # Inner edge: right to left
    for i in range(len(x_side)-1, -1, -1):
        pts_upper.append((x_side[i], y_upper_inner[i]))
        
    c.add_polygon(pts_upper, layer=layer)
    
    # Mirror for lower waveguide
    pts_lower = [(p[0], -p[1]) for p in pts_upper]
    c.add_polygon(pts_lower, layer=layer)
    
    return c

# Generate and save
component = create_splitter()
component.write_gds("component.gds")
print("GDS saved as component.gds")
