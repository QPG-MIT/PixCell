import gdsfactory as gf
import numpy as np

def get_bezier_points(p0, p1, p2, p3, n=100):
    """
    Calculates points for a Cubic Bezier curve.
    p0, p1, p2, p3 are (x, y) tuples.
    """
    t = np.linspace(0, 1, n)
    x = (1-t)**3 * p0[0] + 3*(1-t)**2 * t * p1[0] + 3*(1-t) * t**2 * p2[0] + t**3 * p3[0]
    y = (1-t)**3 * p0[1] + 3*(1-t)**2 * t * p1[1] + 3*(1-t) * t**2 * p2[1] + t**3 * p3[1]
    return np.column_stack((x, y))

@gf.cell
def directional_coupler_final_smooth():
    """
    Directional coupler with smooth Bezier transitions.
    Optimized for exact 120x4 um footprint and smooth visual style.
    """
    c = gf.Component("directional_coupler_final_smooth")
    
    # 1. Dimensions for [120, 4] footprint
    L = 120.0
    H = 4.0
    width = 0.65   # Waveguide width
    gap = 0.3      # Interaction gap
    
    # Segment lengths (Total = 20 + 30 + 20 + 30 + 20 = 120)
    l_lead = 20.0  
    l_bend = 30.0  
    l_mid = 20.0   
    
    # Y-coordinates for centers (Total height = 2 * (y_outer + width/2) = 4.0)
    y_outer = (H / 2) - (width / 2)  # 1.675
    y_inner = (gap / 2) + (width / 2)  # 0.475
    
    # X-coordinates for the centered layout (from -60 to 60)
    x0, x1 = -60.0, -40.0              # Lead-in
    x2 = x1 + l_bend                   # End of first bend (-10)
    x3 = x2 + l_mid                    # End of interaction (10)
    x4 = x3 + l_bend                   # End of second bend (40)
    x5 = 60.0                          # Lead-out

    xs = gf.cross_section.cross_section(width=width, layer=(1, 0))

    def create_arm(y_sign):
        yo = y_sign * y_outer
        yi = y_sign * y_inner
        
        # Build point list for the entire arm
        pts = [(x0, yo), (x1, yo)] # Start lead
        
        # Inward S-bend
        pts.extend(get_bezier_points((x1, yo), (x1 + l_bend/2, yo), (x1 + l_bend/2, yi), (x2, yi))[1:])
        
        # Middle interaction
        pts.append((x3, yi))
        
        # Outward S-bend
        pts.extend(get_bezier_points((x3, yi), (x3 + l_bend/2, yi), (x3 + l_bend/2, yo), (x4, yo))[1:])
        
        # End lead
        pts.append((x5, yo))
        
        # Create Path and extrude
        path = gf.Path(pts)
        return gf.path.extrude(path, cross_section=xs)

    # 2. Add arms to component
    top_arm = c << create_arm(1)
    bot_arm = c << create_arm(-1)
    
    # 3. Add Ports (using standard 'o1', 'o2' naming from extruded path)
    c.add_port("o1", port=top_arm.ports["o1"])
    c.add_port("o2", port=bot_arm.ports["o1"])
    c.add_port("o3", port=bot_arm.ports["o2"])
    c.add_port("o4", port=top_arm.ports["o2"])
    
    return c

if __name__ == "__main__":
    device = directional_coupler_final_smooth()
    
    # Verify exact footprint dimensions
    print(f"Generated Size: {device.xsize:.2f} um x {device.ysize:.2f} um")
    
    # Output
    device.write_gds("coupler_final.gds")
    device.show()