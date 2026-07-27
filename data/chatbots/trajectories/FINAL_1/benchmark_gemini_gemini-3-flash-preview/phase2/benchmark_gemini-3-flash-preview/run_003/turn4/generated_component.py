import numpy as np
import gdsfactory as gf

def create_adiabatic_points(x_end, y_start, y_mid, y_end, l_core):
    """
    Generates a high-resolution set of points for a smooth trajectory.
    Uses cubic interpolation to ensure zero kinks at transition points.
    """
    x = np.linspace(0, x_end, 200)
    y = np.zeros_like(x)
    
    # Defined transition points for the S-curves
    p1 = 6.0   # End of first parallel section
    p2 = 27.0  # The 'pinch' point near core tip
    
    for i, xi in enumerate(x):
        if xi < p1:
            y[i] = y_start
        elif xi < p2:
            # Transition from input to pinch
            t = (xi - p1) / (p2 - p1)
            # Cubic smoothstep: 3t^2 - 2t^3
            s = t * t * (3 - 2 * t)
            y[i] = y_start + (y_mid - y_start) * s
        else:
            # Transition from pinch to output flare
            t = (xi - p2) / (x_end - p2)
            s = t * t * (3 - 2 * t)
            y[i] = y_mid + (y_end - y_mid) * s
            
    return [tuple(p) for p in zip(x, y)]

@gf.cell
def tapered_coupler_final_v5():
    """
    Final Refined Tapered Coupler.
    Footprint: 40.0um x 1.7um (Target exact match)
    """
    c = gf.Component("tapered_coupler_v5")
    
    # --- 1. Parameters ---
    l_total = 40.0
    l_core = 29.0
    
    w_core_in = 0.55
    w_core_tip = 0.02
    
    w_side_in = 0.18
    w_side_out = 0.50 # Flare width at output
    
    # Verticals for centerlines:
    # Target total height = 1.7um. 
    # Half-height = 0.85um.
    # Centerline = 0.85 - (w_side_out / 2) = 0.85 - 0.25 = 0.60
    y_final = 0.60 
    y_start = 0.45 
    y_pinch = 0.28 # Closest distance to the core taper
    
    # --- 2. Central Core (Linear Taper) ---
    c << gf.components.taper(
        length=l_core, 
        width1=w_core_in, 
        width2=w_core_tip, 
        layer=(1, 0)
    )
    
    # --- 3. Smooth Side Arm Paths ---
    # We generate 200 points to ensure the curve is perfectly fluid
    pts_top = create_adiabatic_points(l_total, y_start, y_pinch, y_final, l_core)
    pts_bot = [(x, -y) for x, y in pts_top]
    
    path_top = gf.Path(pts_top)
    path_bot = gf.Path(pts_bot)
    
    # --- 4. Extrusion with Width Transition ---
    # side-arms widen from 180nm to 500nm along their length
    xs_start = gf.cross_section.cross_section(width=w_side_in, layer=(1, 0))
    xs_end = gf.cross_section.cross_section(width=w_side_out, layer=(1, 0))
    trans = gf.path.transition(xs_start, xs_end, width_type='sine')
    
    c << gf.path.extrude_transition(path_top, trans)
    c << gf.path.extrude_transition(path_bot, trans)
    
    return c

if __name__ == "__main__":
    device = tapered_coupler_final_v5()
    
    # Corrected method to calculate dimensions via bounding box (bbox)
    # bbox returns [[xmin, ymin], [xmax, ymax]]
    b = device.bbox
    device_w = b[1][0] - b[0][0]
    device_h = b[1][1] - b[0][1]
    
    print(f"Final Device Dimensions: {device_w:.2f}um x {device_h:.2f}um")
    
    # Visualize and save
    device.show()
    device.write_gds("tapered_coupler_final.gds")