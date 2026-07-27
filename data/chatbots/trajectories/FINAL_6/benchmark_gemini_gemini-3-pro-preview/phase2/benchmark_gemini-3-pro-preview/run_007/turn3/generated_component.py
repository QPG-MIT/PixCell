import gdsfactory as gf
import numpy as np

@gf.cell
def device_star_coupler_optimized():
    """
    Creates a four-arm star/clover device using a custom sine-profile polygon.
    
    Improvements over previous version:
    - Replaces sigmoid 'transition' with a direct parametric polygon construction.
    - Uses a sine-bump width profile (w ~ sin(pi*t)) which provides a non-zero slope
      at the center. This eliminates the "neck" artifact and creates the correct
      sharp 'V' notches between arms at the center.
    - Ensures the "leaf" shape is suitably convex ('fat') to match the target.
    """
    c = gf.Component()
    
    # --- Parameters ---
    # Dimensions derived from footprint (4.7um) and target aspect ratio
    total_radius = 2.35
    len_tip = 0.35
    len_body = total_radius - len_tip  # 2.0 um
    
    w_center = 0.24  # Width at the center intersection
    w_max = 0.98     # Maximum width of the arm (fat leaf shape)
    w_tip = 0.20     # Width of the straight tip section
    
    # --- Build the Parametric Leaf Shape ---
    # We define the upper edge y(x) based on a custom width profile.
    
    num_points = 100
    x = np.linspace(0, len_body, num_points)
    t = x / len_body  # Normalized coordinate [0, 1]
    
    # Width Profile Construction:
    # 1. Linear baseline connecting center width to tip width.
    # 2. Additive Sine bump to create the expansion.
    #    The sine term adds convexity. At t=0 and t=1, sin(pi*t)=0, so it connects perfectly.
    #    We solve for 'delta' such that the max width at t=0.5 equals w_max.
    
    w_linear = w_center + (w_tip - w_center) * t
    delta = w_max - (w_center + w_tip) / 2.0
    width_profile = w_linear + delta * np.sin(np.pi * t)
    
    # Calculate y-coordinates for the polygon (half-width)
    y_upper = width_profile / 2.0
    y_lower = -y_upper
    
    # --- Construct Polygon Points ---
    points = []
    
    # 1. Trace Top Edge of Body (Center -> Tip Start)
    for i in range(len(x)):
        points.append((x[i], y_upper[i]))
    
    # 2. Trace the Tip (Straight Rectangle)
    #    Extends from len_body to total_radius
    points.append((len_body + len_tip, w_tip/2))   # Top-Right
    points.append((len_body + len_tip, -w_tip/2))  # Bottom-Right
    
    # 3. Trace Bottom Edge of Body (Tip Start -> Center)
    #    Iterate backwards to close the polygon loop
    for i in range(len(x)-1, -1, -1):
        points.append((x[i], y_lower[i]))
        
    # --- Create Leaf Component ---
    leaf = gf.Component()
    leaf.add_polygon(points, layer=(1, 0))
    
    # Add port at the tip
    leaf.add_port(
        name="o1", 
        center=(len_body + len_tip, 0), 
        width=w_tip, 
        orientation=0, 
        layer=(1, 0)
    )
    
    # --- Assemble Full Device ---
    # Place 4 leaves rotated by 90 degrees around the center
    for i, angle in enumerate([0, 90, 180, 270]):
        ref = c << leaf
        ref.rotate(angle)
        # Leaves are generated starting at (0,0), so no translation needed
        c.add_port(f"o{i+1}", port=ref.ports["o1"])

    return c

if __name__ == "__main__":
    component = device_star_coupler_optimized()
    component.write_gds("star_device_optimized.gds")
    component.show()