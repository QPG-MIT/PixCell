import gdsfactory as gf
import numpy as np

@gf.cell
def device_star_coupler_optimized():
    """
    Creates a four-arm star/clover device matching the visual target.
    
    Key features:
    - 4-fold rotational symmetry.
    - Arms meet at a sharp point in the center (width=0).
    - Arms have a 'fat' sine-based profile.
    - Arms end in a straight rectangular waveguide tip.
    """
    c = gf.Component()
    
    # --- Dimensions ---
    # Total footprint constraint: 4.7 x 4.7 um -> Radius = 2.35 um
    total_radius = 2.35
    
    # The tip is the straight section at the end
    len_tip = 0.35
    width_tip = 0.2
    
    # The body is the curved section
    len_body = total_radius - len_tip  # 2.0 um
    
    # Center width 0 creates the sharp "V" notch between arms at the origin
    # This fixes the "boxy" center artifact from the previous iteration.
    width_center = 0.0 
    
    # Maximum width of the leaf (tuning 'fatness')
    width_max = 0.98
    
    # --- Shape Generation ---
    # Create parametric width profile w(x)
    num_points = 100
    x = np.linspace(0, len_body, num_points)
    t = x / len_body  # Normalized 0..1
    
    # Profile Logic: Linear taper + Sine bump
    # We want max width roughly in the middle.
    # Base linear taper: w = w_center + (w_tip - w_center)*t
    # Bump: delta * sin(pi*t)
    # Calculate delta to enforce max width:
    w_linear_mid = width_center + (width_tip - width_center) * 0.5
    delta = width_max - w_linear_mid
    
    w_profile = width_center + (width_tip - width_center) * t + delta * np.sin(np.pi * t)
    
    # Calculate envelope coordinates (half-width)
    y_upper = w_profile / 2.0
    y_lower = -y_upper
    
    # Construct point list for Polygon
    points = []
    
    # 1. Top edge of body (Center -> Tip Start)
    for i in range(len(x)):
        points.append((x[i], y_upper[i]))
        
    # 2. Tip (Straight Rectangle) - Top Right -> Bottom Right
    points.append((total_radius, width_tip / 2.0))
    points.append((total_radius, -width_tip / 2.0))
    
    # 3. Bottom edge of body (Tip Start -> Center) - Backwards
    for i in range(len(x)-1, -1, -1):
        points.append((x[i], y_lower[i]))
        
    # --- Create Leaf and Array ---
    leaf = gf.Component()
    leaf.add_polygon(points, layer=(1, 0))
    
    # Add port for reference
    leaf.add_port(
        name="o1", 
        center=(total_radius, 0), 
        width=width_tip, 
        orientation=0, 
        layer=(1, 0)
    )
    
    # Place 4 rotated copies around the center
    # Because width_center=0, they all touch precisely at (0,0)
    for i, angle in enumerate([0, 90, 180, 270]):
        ref = c << leaf
        ref.rotate(angle)
        c.add_port(f"o{i+1}", port=ref.ports["o1"])

    return c

if __name__ == "__main__":
    component = device_star_coupler_optimized()
    component.write_gds("star_device_optimized.gds")
    component.show()