import gdsfactory as gf
import math

@gf.cell
def star_coupler_device():
    """
    Creates a 4-pointed star geometric device within a 4.7um x 4.7um footprint.
    Refined parameters match the target's broader central lobes and thinner ports.
    """
    c = gf.Component()
    
    # =========================================================================
    # Parameters
    # =========================================================================
    # Device Constraints
    footprint_side = 4.7
    half_size = footprint_side / 2.0  # 2.35 um
    
    # Port configuration
    # Thinner width (0.35) and shorter length (0.5) to match the visual proportions
    # of the target, emphasizing the curved body.
    port_width = 0.35        
    port_length = 0.5       
    
    # Geometry tuning
    # x_meet is the coordinate where the straight port connects to the curved body.
    # We calculate the ellipse such that it naturally tapers to 'port_width' at this exact x.
    x_meet = half_size - port_length  # 1.85 um
    
    # Ellipse Minor Radius
    # Increased to 0.6um (full width 1.2um) to create the "fatter" leaf/star shape.
    r_minor = 0.6 
    
    # Ellipse Major Radius Calculation
    # Solve (x_meet/a)^2 + (y_meet/b)^2 = 1 for 'a'
    # where y_meet is half the port width.
    y_meet = port_width / 2.0
    
    # Safety check
    if y_meet >= r_minor:
        raise ValueError("Port width must be smaller than twice the minor radius.")
        
    term = 1 - (y_meet / r_minor)**2
    r_major = x_meet / math.sqrt(term)
    
    layer = (1, 0)

    # =========================================================================
    # Primitives construction
    # =========================================================================
    
    # 1. Central Body (Intersecting Ellipses)
    # The star shape is formed by the union of a horizontal and vertical ellipse.
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
    # Define a generic rectangular port component
    rect_port = gf.components.rectangle(
        size=(port_length, port_width), 
        layer=layer, 
        centered=True
    )
    
    # Calculate center position for the port rectangles
    # The rectangle must fill the space from x_meet to half_size.
    # Its center is therefore at: x_meet + (port_length / 2)
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