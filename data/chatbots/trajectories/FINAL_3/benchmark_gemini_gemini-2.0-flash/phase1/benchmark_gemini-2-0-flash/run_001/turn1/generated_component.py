import gdsfactory as gf
from gdsfactory.components import straight, bend_euler
from gdsfactory.routing import route_single

@gf.cell
def mzi_coupler(length=120, bend_radius=10, coupler_length=10, coupler_gap=0.2):
    """
    Mach-Zehnder interferometer with directional coupler.

    Args:
        length: Total length of the MZI.
        bend_radius: Radius of the Euler bends.
        coupler_length: Length of the directional coupler waveguides.
        coupler_gap: Gap between the directional coupler waveguides.
    """
    c = gf.Component("mzi_coupler")

    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))

    # Input straight waveguide
    straight_in = straight(length=coupler_length, cross_section=xs)
    straight_in_ref = c << straight_in

    # First coupler
    coupler = gf.components.coupler_straight(length=coupler_length, gap=coupler_gap, cross_section=xs)
    coupler_ref = c << coupler
    coupler_ref.connect("o1", straight_in_ref.ports["o2"])

    # Top arm of the MZI
    bend_top1 = bend_euler(radius=bend_radius, angle=90, cross_section=xs)
    bend_top1_ref = c << bend_top1
    bend_top1_ref.connect("o1", coupler_ref.ports["o3"])

    straight_top = straight(length=length - 2*bend_radius - coupler_length, cross_section=xs)
    straight_top_ref = c << straight_top
    straight_top_ref.connect("o1", bend_top1_ref.ports["o2"])
    
    bend_top2 = bend_euler(radius=bend_radius, angle=90, cross_section=xs)
    bend_top2_ref = c << bend_top2
    bend_top2_ref.connect("o1", straight_top_ref.ports["o2"])

    # Bottom arm of the MZI
    bend_bottom1 = bend_euler(radius=bend_radius, angle=90, cross_section=xs)
    bend_bottom1_ref = c << bend_bottom1
    bend_bottom1_ref.connect("o1", coupler_ref.ports["o4"])

    straight_bottom = straight(length=length - 2*bend_radius - coupler_length, cross_section=xs)
    straight_bottom_ref = c << straight_bottom
    straight_bottom_ref.connect("o1", bend_bottom1_ref.ports["o2"])
    
    bend_bottom2 = bend_euler(radius=bend_radius, angle=90, cross_section=xs)
    bend_bottom2_ref = c << bend_bottom2
    bend_bottom2_ref.connect("o1", straight_bottom_ref.ports["o2"])

    # Second coupler
    coupler2 = gf.components.coupler_straight(length=coupler_length, gap=coupler_gap, cross_section=xs)
    coupler2_ref = c << coupler2
    coupler2_ref.connect("o3", bend_top2_ref.ports["o2"])
    coupler2_ref.connect("o4", bend_bottom2_ref.ports["o2"])
    
    # Output straight waveguides
    straight_out1 = straight(length=coupler_length, cross_section=xs)
    straight_out1_ref = c << straight_out1
    straight_out1_ref.connect("o1", coupler2_ref.ports["o1"])

    straight_out2 = straight(length=coupler_length, cross_section=xs)
    straight_out2_ref = c << straight_out2
    straight_out2_ref.connect("o1", coupler2_ref.ports["o2"])
    
    # Add ports
    c.add_port("o1", port=straight_in_ref.ports["o1"])
    c.add_port("o2", port=straight_out1_ref.ports["o2"])
    c.add_port("o3", port=straight_out2_ref.ports["o2"])
    
    return c


if __name__ == "__main__":
    mzi = mzi_coupler()
    mzi.show()  # Remove show_ports=True
    # You can also save the component to a GDS file
    # mzi.write_gds("mzi_coupler.gds")