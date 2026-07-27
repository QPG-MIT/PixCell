import numpy as np
import gdsfactory as gf

@gf.cell
def symmetric_coupler_smooth_v4():
    """
    Turn 4 (Fixed): Using explicit point-based Path to ensure compatibility and smoothness.
    Footprint: 18um x 3um.
    """
    c = gf.Component("symmetric_coupler_v4")
    
    # 1. Design Parameters
    length = 18.0
    total_height = 3.0
    width = 0.8    # Waveguide width
    gap = 0.2      # Minimum gap at center
    
    # Calculation for centerline y-coordinates to hit exactly 3.0um height
    # y_end (at ports) + half_width = 1.5  => y_end = 1.1
    # y_mid (at center) = (width + gap) / 2 => y_mid = 0.5
    y_end = 1.1
    y_mid = 0.5
    amplitude = y_end - y_mid  # 0.6um dip
    
    # 2. Generate Smooth Path Points
    # We use a sin^2 function: y = y_end - amplitude * sin^2(pi * x / length)
    num_points = 100
    x_vals = np.linspace(0, length, num_points)
    y_vals = y_end - amplitude * np.sin(np.pi * x_vals / length)**2
    
    points = np.column_stack((x_vals, y_vals))
    
    # Create Path object and cross-section
    path = gf.Path(points)
    xs = gf.cross_section.cross_section(width=width, layer=(1, 0))
    
    # 3. Add Arms
    # Top Arm
    top_arm = c << gf.path.extrude(path, cross_section=xs)
    
    # Bottom Arm (Mirror of top arm across y=0)
    bot_arm = c << gf.path.extrude(path, cross_section=xs)
    bot_arm.mirror_y()
    
    # 4. Define Ports
    # Ports are automatically created at path ends by extrude()
    c.add_port("o1", port=top_arm.ports["o1"])
    c.add_port("o2", port=bot_arm.ports["o1"])
    c.add_port("o3", port=top_arm.ports["o2"])
    c.add_port("o4", port=bot_arm.ports["o2"])
    
    return c

if __name__ == "__main__":
    # Create the component
    component = symmetric_coupler_smooth_v4()
    
    # Verify dimensions
    bbox = component.dbbox()
    print(f"Final device dimensions: {bbox.width():.2f}um x {bbox.height():.2f}um")
    
    # Save and view
    component.write_gds("symmetric_coupler_v4.gds")
    component.show()