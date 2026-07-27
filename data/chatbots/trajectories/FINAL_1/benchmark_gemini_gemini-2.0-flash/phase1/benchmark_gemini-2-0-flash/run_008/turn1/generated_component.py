import gdsfactory as gf
from gdsfactory.components import straight, bend_euler, taper

@gf.cell
def recreated_device():
    c = gf.Component("recreated_device")

    # Cross-section definition
    width = 0.5  # Example width
    radius_min = 10.0  # Minimum bend radius for the cross-section
    xs = gf.cross_section.cross_section(width=width, layer=(1, 0), radius=radius_min)
    xs_tapered = gf.cross_section.cross_section(width=1.0, layer=(1, 0), radius=radius_min)  # Cross section for wider waveguide

    # Initial straight segments
    straight1 = c << straight(length=5, cross_section=xs)
    straight2 = c << straight(length=5, cross_section=xs)
    straight3 = c << straight(length=5, cross_section=xs)

    # Position straights vertically
    vertical_spacing = 0.7  # Example spacing, adjust based on target footprint
    straight2.movey(vertical_spacing)
    straight3.movey(-vertical_spacing)

    # Tapers
    taper_length = 5
    taper_width2 = 1.0  # Wider width after taper
    taper1 = c << taper(length=taper_length, width1=width, width2=taper_width2)
    taper2 = c << taper(length=taper_length, width1=width, width2=taper_width2)
    taper3 = c << taper(length=taper_length, width1=width, width2=width) # No width change for middle taper

    # Connect tapers
    taper1.connect("o1", straight2.ports["o2"])
    taper2.connect("o1", straight3.ports["o2"])
    taper3.connect("o1", straight1.ports["o2"])

    # Bends
    bend_radius = radius_min # Must be greater than or equal to the minimum radius
    bend1 = c << bend_euler(radius=bend_radius, angle=90, cross_section=xs_tapered)
    bend2 = c << bend_euler(radius=bend_radius, angle=-90, cross_section=xs_tapered)  # Invert rotation
    bend3 = c << bend_euler(radius=bend_radius, angle=90, cross_section=xs_tapered)
    bend4 = c << bend_euler(radius=bend_radius, angle=-90, cross_section=xs_tapered)

    # Connect Taper 1 to Bends
    bend1.connect("o1", taper1.ports["o2"])
    bend2.connect("o2", taper1.ports["o2"])

    # Connect Taper 2 to Bends
    bend3.connect("o1", taper2.ports["o2"])
    bend4.connect("o2", taper2.ports["o2"])

    # Final Straight Sections after bends
    straight4 = c << straight(length=10, cross_section=xs_tapered) # Adjust length
    straight5 = c << straight(length=10, cross_section=xs_tapered) # Adjust length

    # Connect Bends to Final Straight Sections
    straight4.connect("o1", bend1.ports["o2"])
    straight5.connect("o1", bend3.ports["o2"])

    # Port Definitions
    c.add_port("o1", port=straight1.ports["o1"])
    c.add_port("o2", port=straight4.ports["o2"])
    c.add_port("o3", port=straight5.ports["o2"])


    return c

if __name__ == "__main__":
    device = recreated_device()
    device.show()
    print(device.get_ports())