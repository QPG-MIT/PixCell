import gdsfactory as gf
import numpy as np

@gf.cell
def adiabatic_coupler_smooth():
    """
    Recreates the adiabatic coupler using a mathematical S-curve 
    to ensure perfectly smooth, kink-free transitions.
    """
    c = gf.Component("smooth_adiabatic_coupler")
    
    # 1. Design Parameters (Matched to 18x3 um footprint)
    length = 18.0
    width = 0.82      # Adjusted for visual match
    center_gap = 0.16 # Defined gap at the pinch point
    
    # Vertical calculations for waveguide centers
    # At ends: y_outer = 1.09 (Top edge at 1.09 + 0.41 = 1.5, reaching the 3um boundary)
    y_outer = 1.09 
    # At center: y_inner = (gap/2) + (width/2)
    y_inner = (center_gap / 2) + (width / 2)
    
    # 2. Generate Path Points mathematically
    # We use an S-curve equation: y = y_start + dy * (x/L - sin(2*pi*x/L)/(2*pi))
    # This ensures zero derivative and zero curvature at all join points.
    num_points = 120
    x = np.linspace(0, length, num_points)
    y = np.zeros(num_points)
    
    # Divide into two halves for the dip
    half_idx = num_points // 2
    L_half = length / 2
    
    # First half: Transition from outer to inner
    x_h1 = x[:half_idx]
    y[:half_idx] = y_outer + (y_inner - y_outer) * (x_h1/L_half - np.sin(2*np.pi*x_h1/L_half)/(2*np.pi))
    
    # Second half: Transition from inner back to outer
    x_h2 = x[half_idx:] - L_half
    y[half_idx:] = y_inner + (y_outer - y_inner) * (x_h2/L_half - np.sin(2*np.pi*x_h2/L_half)/(2*np.pi))
    
    # Create the Top Path
    points_top = list(zip(x, y))
    path_top = gf.Path(points_top)
    
    # Create the Bottom Path (Mirror of top)
    points_bot = [(px, -py) for px, py in points_top]
    path_bot = gf.Path(points_bot)
    
    # 3. Extrude and Add to Component
    xs = gf.cross_section.cross_section(width=width, layer=(1, 0))
    top_arm = c << gf.path.extrude(path_top, cross_section=xs)
    bot_arm = c << gf.path.extrude(path_bot, cross_section=xs)
    
    # 4. Define Ports for connectivity
    c.add_port("o1", port=top_arm.ports["o1"])
    c.add_port("o2", port=top_arm.ports["o2"])
    c.add_port("o3", port=bot_arm.ports["o1"])
    c.add_port("o4", port=bot_arm.ports["o2"])

    return c

if __name__ == "__main__":
    # Initialize component
    device = adiabatic_coupler_smooth()
    
    # Write GDS
    device.write_gds("smooth_adiabatic_coupler.gds")
    
    print("GDS file 'smooth_adiabatic_coupler.gds' has been generated.")
    print(f"Final Footprint: {device.size_info.width:.1f}um x {device.size_info.height:.1f}um")