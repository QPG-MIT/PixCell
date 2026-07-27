import gdsfactory as gf

@gf.cell
def y_branch():
    c = gf.Component()
    
    # Define cross-section (0.5um wide waveguide on layer (1,0))
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # === Left straight section (common start) ===
    straight_length = 10.0
    wg_left = c << gf.components.straight(length=straight_length, cross_section=xs)
    
    # === Create two smooth diverging paths ===
    # We'll use Euler bends for smooth, adiabatic transitions
    
    # Parameters for divergence
    bend_radius = 15.0
    bend_angle = 25.0  # degrees
    
    # Upper branch
    bend_upper = c << gf.components.bend_euler(radius=bend_radius, angle=bend_angle, cross_section=xs)
    bend_upper.connect("o1", wg_left.ports["o2"])
    
    # Lower branch
    bend_lower = c << gf.components.bend_euler(radius=bend_radius, angle=-bend_angle, cross_section=xs)
    bend_lower.connect("o1", wg_left.ports["o2"])
    
    # === Right straight sections ===
    right_length = 15.0
    wg_upper_right = c << gf.components.straight(length=right_length, cross_section=xs)
    wg_lower_right = c << gf.components.straight(length=right_length, cross_section=xs)
    
    wg_upper_right.connect("o1", bend_upper.ports["o2"])
    wg_lower_right.connect("o1", bend_lower.ports["o2"])
    
    # === Add ports ===
    c.add_port("o1", port=wg_left.ports["o1"])           # Left input
    c.add_port("o2", port=wg_upper_right.ports["o2"])    # Upper output
    c.add_port("o3", port=wg_lower_right.ports["o2"])    # Lower output
    
    # === Flatten to avoid off-grid instance errors ===
    c.flatten()
    
    return c

# Create and save the device
device = y_branch()
device.write_gds("y_branch.gds")