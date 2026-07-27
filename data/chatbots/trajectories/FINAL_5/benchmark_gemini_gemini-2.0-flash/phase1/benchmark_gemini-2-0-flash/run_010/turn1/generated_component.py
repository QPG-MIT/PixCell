import gdsfactory as gf
from gdsfactory.component import Component

@gf.cell
def my_device() -> Component:
    """Recreates the geometry in the attached PNG using GDSFactory parametric functions."""
    c = gf.Component("my_device")

    # Define cross-section (width=0.5, layer=(1, 0))
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0), radius=4.0)  # set min radius = bend radius

    # Parameters (tuned by visual inspection)
    straight_length = 2.2
    bend_radius = 4.0
    coupler_length = 8.0
    coupler_gap = 0.15  # Smaller than default for tight coupling
    taper_length = 2.0
    rib_length = 1.4
    rib_separation = 0.04  # The gap between ribs


    # Upper waveguide structure
    # 1. Straight section
    straight1 = c << gf.components.straight(length=straight_length, cross_section=xs)

    # 2. Bend
    bend1 = c << gf.components.bend_circular(radius=bend_radius, angle=90, cross_section=xs)
    bend1.connect("o1", straight1.ports["o2"])

    # 3. Straight coupler section with grating-like structure
    coupler_straight1 = c << gf.components.straight(length=coupler_length, cross_section=xs)
    coupler_straight1.connect("o1", bend1.ports["o2"])

    # Add grating-like structure on top of coupler_straight1
    num_ribs = int(coupler_length / (rib_length + rib_separation))

    for i in range(num_ribs):
      x_offset = i * (rib_length + rib_separation) - coupler_length/2 + (rib_length + rib_separation)/2 #center at 0
      rib = c << gf.components.rectangle(size=(rib_length, xs.width), layer=(1, 0), centered=True)
      rib.move((x_offset, xs.width))
      rib.connect("o1", coupler_straight1.ports["o1"]) #dummy to keep the reference

    # 4. Taper to pointed tip
    taper1 = c << gf.components.taper(length=taper_length, width1=xs.width, width2=0.05)
    taper1.connect("o1", coupler_straight1.ports["o2"])

    # Lower waveguide structure (mirrored)
    # 1. Straight section
    straight2 = c << gf.components.straight(length=straight_length, cross_section=xs)
    straight2.mirror()

    # 2. Bend
    bend2 = c << gf.components.bend_circular(radius=bend_radius, angle=90, cross_section=xs)
    bend2.mirror()
    bend2.connect("o1", straight2.ports["o2"])

    # 3. Straight coupler section with grating-like structure
    coupler_straight2 = c << gf.components.straight(length=coupler_length, cross_section=xs)
    coupler_straight2.mirror()
    coupler_straight2.connect("o1", bend2.ports["o2"])


    # Add grating-like structure on top of coupler_straight2
    for i in range(num_ribs):
      x_offset = i * (rib_length + rib_separation) - coupler_length/2 + (rib_length + rib_separation)/2 #center at 0
      rib = c << gf.components.rectangle(size=(rib_length, xs.width), layer=(1, 0), centered=True)
      rib.move((x_offset, -xs.width))
      rib.connect("o1", coupler_straight2.ports["o1"]) #dummy to keep the reference

    # 4. Taper to pointed tip
    taper2 = c << gf.components.taper(length=taper_length, width1=xs.width, width2=0.05)
    taper2.mirror()
    taper2.connect("o1", coupler_straight2.ports["o2"])

    # Position Lower structure relative to upper structure.
    vertical_spacing = 0.7

    straight2.movey(-vertical_spacing -2*xs.width) #xs.width for rib height
    bend2.movey(-vertical_spacing -2*xs.width)
    coupler_straight2.movey(-vertical_spacing -2*xs.width)
    taper2.movey(-vertical_spacing -2*xs.width)


    # Connecting line between grating structures
    connecting_line = c << gf.components.straight(length=coupler_length, cross_section=gf.cross_section.cross_section(width=0.06, layer=(1, 0))) #Thin Line
    connecting_line.movey(-vertical_spacing/2 -xs.width) #Center it. XS width here is also the rib width, making it perfect.

    return c

if __name__ == "__main__":
    device = my_device()
    device.show(show_ports=True)
    device.write_gds("my_device.gds")