import gdsfactory as gf
import numpy as np

@gf.cell
def star_coupler_device():
    """
    Creates a 4-pointed star geometric device using sine-tapered arms
    to match the smooth 'leaf' shape and seamless port transitions of the target.
    Footprint constrained to 4.7um x 4.7um.
    """
    c = gf.Component()
    
    # =========================================================================
    # Parameters
    # =========================================================================
    # Device Constraints
    footprint_side = 4.7
    half_size = footprint_side / 2.0  # 2.35 um
    
    # Port configuration
    # Width adjusted to 0.45um for better visual proportion with the body.
    port_width = 0.45
    # Length of the straight output section. 
    # Short straight section allows the tapered body to dominate the shape.
    port_length = 0.3       
    
    # Body Geometry
    # The 'star' is formed by 4 arms meeting at the center.
    # The arms taper from a wide center to the narrow port.
    # A width of 1.3um at the center creates the 'fat' overlapping hub.
    center_width = 1.3
    
    # Length of the tapered section
    taper_length = half_size - port_length

    # Layer
    layer = (1, 0)

    # =========================================================================
    # Geometry Construction: Parametric Sine Lobe
    # =========================================================================
    
    # We generate the points for one arm explicitly to control the curvature.
    # We use a cosine-squared (sine) profile for an S-curve taper.
    # This ensures the slope is 0 at the port (smooth transition) 
    # and 0 at the center (smooth hub).
    
    num_points = 100
    x = np.linspace(0, taper_length, num_points)
    
    # Taper function: y(x)
    # x=0 -> y=center_width/2
    # x=L -> y=port_width/2
    # Profile: y = min + (max-min) * (1 + cos(pi*x/L))/2
    amp = (center_width - port_width) / 2.0
    y = (port_width / 2.0) + amp * 0.5 * (1 + np.cos(np.pi * x / taper_length))
    
    # Construct the polygon points for the arm
    # Top edge (x, y)
    pts_top = list(zip(x, y))
    # Bottom edge (x, -y) in reverse order to close loop
    pts_bot = list(zip(x, -y))
    pts_arm = pts_top + pts_bot[::-1]
    
    # Create the single arm component (Taper + Straight Port)
    arm = gf.Component()
    
    # 1. Add Taper Polygon
    arm.add_polygon(pts_arm, layer=layer)
    
    # 2. Add Straight Port Extension
    # Rectangle centered at (taper_length + port_length/2, 0)
    port_rect = gf.components.rectangle(
        size=(port_length, port_width),
        layer=layer,
        centered=True
    )
    p_ref = arm << port_rect
    p_ref.move((taper_length + port_length / 2.0, 0))
    
    # Define the port on the arm component for easy arraying
    arm.add_port(
        name="tip", 
        center=(half_size, 0), 
        width=port_width, 
        orientation=0, 
        layer=layer
    )

    # =========================================================================
    # Assembly
    # =========================================================================
    
    # Place 4 rotated copies of the arm
    angles = [0, 90, 180, 270]
    port_names = ["o1", "o3", "o2", "o4"] # Standard E, N, W, S ordering
    
    for angle, name in zip(angles, port_names):
        ref = c << arm
        ref.rotate(angle)
        
        # We need to expose the ports correctly. 
        # Since the arm is rotated around (0,0), the port follows.
        # We transform the port from the reference to the main component.
        c.add_port(name=name, port=ref.ports["tip"])

    return c

if __name__ == "__main__":
    component = star_coupler_device()
    component.show()
    component.write_gds("star_coupler_refined.gds")