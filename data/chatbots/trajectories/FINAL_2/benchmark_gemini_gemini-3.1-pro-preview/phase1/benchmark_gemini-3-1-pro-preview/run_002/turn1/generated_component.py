import gdsfactory as gf

@gf.cell
def mmi_1x4_custom():
    """
    Creates a 1x4 MMI with tapered ports that perfectly fits a 25x10 footprint.
    Total width = 25 um
    Total height = 1.5 (bottom taper) + 5.0 (rectangle) + 3.5 (top tapers) = 10 um
    """
    c = gf.Component("mmi_1x4_custom")
    layer = (1, 0)
    
    # Define a cross-section to pass layer and default width info to routing primitives
    xs = gf.cross_section.cross_section(width=1.0, layer=layer)

    # 1. Main MMI rectangular body
    # Spans from x = -12.5 to 12.5 (Width: 25) and y = -2.5 to 2.5 (Height: 5)
    c << gf.components.rectangle(size=(25, 5), centered=True, layer=layer)

    # 2. Top Output Structures (4x)
    # Total height of top protrusion = 3.5 um (Taper: 2.0, Straight: 1.5)
    taper_top = gf.components.taper(length=2.0, width1=4.0, width2=1.0, cross_section=xs)
    straight_top = gf.components.straight(length=1.5, cross_section=xs)

    # Distribute the 4 output ports evenly across the 25um width
    x_positions = [-9.0, -3.0, 3.0, 9.0]

    for x in x_positions:
        # Add and orient the taper part pointing upwards
        t_ref = c << taper_top
        t_ref.rotate(90)
        # Move base ('o1') to rest exactly on the top edge of the rectangle (y=2.5)
        t_ref.move((x, 2.5)) 

        # Add and connect the straight waveguide section
        s_ref = c << straight_top
        # Use component assembly pattern to seamlessly snap ports together
        # (Connect automatically aligns angle and position)
        s_ref.connect("o1", t_ref.ports["o2"])

    # 3. Bottom Input Structure (1x)
    # Total height of bottom protrusion = 1.5 um
    taper_bot = gf.components.taper(length=1.5, width1=5.0, width2=1.5, cross_section=xs)

    # Add and orient the taper part pointing downwards
    b_ref = c << taper_bot
    b_ref.rotate(-90)
    # Move base ('o1', the wide part) to rest exactly on the bottom edge (y=-2.5)
    b_ref.move((0, -2.5))

    return c

if __name__ == "__main__":
    # Generate the component
    device = mmi_1x4_custom()
    
    # Uncomment the following line to view the generated device in KLayout
    # device.show()