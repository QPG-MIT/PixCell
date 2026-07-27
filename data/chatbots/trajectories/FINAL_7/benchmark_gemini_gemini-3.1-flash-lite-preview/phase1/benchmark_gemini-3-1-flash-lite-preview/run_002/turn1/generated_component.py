import gdsfactory as gf

@gf.cell
def mzi_with_housing():
    c = gf.Component()
    
    # 1. Define a single, shared CrossSection to prevent PortWidthMismatch
    # radius_min is set to 1.0 to allow for tight bends
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0), radius_min=1.0)

    # 2. Build the Outer Housing (using racetrack for parametric control)
    # A racetrack is essentially the outer "capsule" shape seen in the image
    outer_housing = c << gf.components.racetrack(
        racetrack_radius=3.0, 
        length_x=6.0, 
        cross_section=xs
    )

    # 3. Build the Inner Structure (the two straight waveguides)
    # We place them manually to avoid automatic routing width mismatches
    inner_top = c << gf.components.straight(length=4.0, cross_section=xs)
    inner_bot = c << gf.components.straight(length=4.0, cross_section=xs)

    # 4. Position the inner waveguides
    # Center them vertically and horizontally inside the outer housing
    inner_top.movey(1.5)
    inner_top.movex(-2.0)
    
    inner_bot.movey(-1.5)
    inner_bot.movex(-2.0)

    return c

# Generate and visualize
device = mzi_with_housing()
device.show()