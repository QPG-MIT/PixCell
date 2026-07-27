import gdsfactory as gf

@gf.cell
def coupler_device():
    """
    Creates a smooth, adiabatic pinch coupler using path chaining.
    """
    c = gf.Component()
    xs = gf.cross_section.cross_section(width=0.4, layer=(1, 0))

    # 1. Create the path for the top waveguide
    # We chain primitives to create a smooth, continuous curve
    # The sequence: Straight -> Bend In -> Bend Out -> Straight
    p = gf.Path()
    p.append(gf.path.straight(length=5))
    p.append(gf.path.euler(radius=10, angle=-8)) # Bend inward
    p.append(gf.path.euler(radius=10, angle=8))   # Bend outward
    p.append(gf.path.straight(length=5))

    # 2. Extrude the paths
    # This turns the mathematical path into a physical GDS geometry
    wg_top_ref = c << gf.path.extrude(p, cross_section=xs)
    wg_bot_ref = c << gf.path.extrude(p, cross_section=xs)

    # 3. Position the waveguides
    # Place top waveguide shifted up
    wg_top_ref.movey(0.7)
    
    # Mirror the bottom waveguide to make it curve towards the top one
    wg_bot_ref.mirror(p1=(0, 0), p2=(1, 0))
    wg_bot_ref.movey(-0.7)

    return c

# Generate the component
device = coupler_device()

# Save/Show
device.write_gds("coupler_device.gds")
device.show()