import gdsfactory as gf
import math

@gf.cell
def star_coupler_device():
    """
    Creates a 4-pointed star geometric device within a 4.7um x 4.7um footprint.
    Uses tuned ellipse parameters to achieve sharp inward cusps and smooth port transitions.
    """
    c = gf.Component()
    
    # =========================================================================
    # Parameters
    # =========================================================================
    # Device Constraints
    footprint_side = 4.7
    half_size = footprint_side / 2.0  # 2.35 um
    
    # Port configuration
    port_width = 0.4        # Width of the straight waveguide section
    port_length = 0.6       # Length of the straight waveguide section
    
    # Geometry tuning
    # x_meet is the coordinate where the straight port connects to the curved body
    x_meet = half_size - port_length  # 1.75 um
    
    # Ellipse Minor Radius
    # Reduced to 0.5um to create the sharp, non-blobby star shape
    r_minor = 0.5 
    
    # Ellipse Major Radius Calculation
    # We solve the ellipse equation (x/a)^2 + (y/b)^2 = 1 for 'a' (major radius).
    # Condition: At x = x_meet, width must be port_width (y = port_width/2).
    # This guarantees the ellipse lines up perfectly with the rectangle.
    y_meet = port_width / 2.0
    
    # Check to avoid math domain error (port must be narrower than lobe)
    if y_meet >= r_minor:
        raise ValueError("Port width must be smaller than twice the minor radius.")
        
    # Math: (x_meet/a)^2 = 1 - (y_meet/r_minor)^2
    # a = x_meet / sqrt(1 - (y_meet/r_minor)^2)
    term = 1 - (y_meet / r_minor)**2
    r_major = x_meet / math.sqrt(term)
    
    layer = (1, 0)

    # =========================================================================
    # Primitives
    # =========================================================================
    
    # 1. Central Body (Intersecting Ellipses)
    # Horizontal lobe
    c << gf.components.ellipse(
        radii=(r_major, r_minor), 
        layer=layer
    )
    # Vertical lobe
    c << gf.components.ellipse(
        radii=(r_minor, r_major), 
        layer=layer
    )

    # 2. Ports (Rectangular Extensions)
    # Define generic port rectangle
    rect_port = gf.components.rectangle(
        size=(port_length, port_width), 
        layer=layer, 
        centered=True
    )
    
    # Calculate offset for the rectangle center
    # The rectangle spans from [half_size - port_length] to [half_size]
    # Center is at half_size - (port_length / 2)
    offset = half_size - (port_length / 2.0)

    # Place Port 1 (East)
    p1 = c << rect_port
    p1.move((offset, 0))
    c.add_port(name="o1", center=(half_size, 0), width=port_width, orientation=0, layer=layer)

    # Place Port 2 (West)
    p2 = c << rect_port
    p2.move((-offset, 0))
    c.add_port(name="o2", center=(-half_size, 0), width=port_width, orientation=180, layer=layer)

    # Place Port 3 (North)
    p3 = c << rect_port
    p3.rotate(90)
    p3.move((0, offset))
    c.add_port(name="o3", center=(0, half_size), width=port_width, orientation=90, layer=layer)

    # Place Port 4 (South)
    p4 = c << rect_port
    p4.rotate(90)
    p4.move((0, -offset))
    c.add_port(name="o4", center=(0, -half_size), width=port_width, orientation=270, layer=layer)

    return c

if __name__ == "__main__":
    component = star_coupler_device()
    component.show()
    component.write_gds("star_coupler_refined.gds")