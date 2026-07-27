import gdsfactory as gf

@gf.cell
def t_shaped_structures(
    width=2,
    length=5,
    radius=10,  # Modified radius
    separation=10,
    layer=(1, 0),
):
    """Creates two T-shaped structures with rounded caps, one above the other.

    Args:
        width: Width of the T-structure's stem.
        length: Length of the T-structure's cap.
        radius: Radius of the rounded cap.
        separation: Vertical separation between the two T-structures.
        layer: The GDS layer to put the geometries on.

    Returns:
        A Component containing the two T-shaped structures.
    """

    c = gf.Component("t_shaped_structures")

    # Create cross-section
    xs = gf.cross_section.cross_section(width=width, layer=layer, radius=radius)  # Modified xs to include radius


    # Create the top T-structure
    top_rect = c << gf.components.rectangle(size=(length, width), layer=layer, centered=True)
    top_rect.movex(-length/2)
    top_rect.movey(width/2)
    
    top_bend1 = c << gf.components.bend_circular(radius=radius, angle=90, cross_section=xs)
    top_bend1.connect('o1', top_rect.ports['o2'])

    top_bend2 = c << gf.components.bend_circular(radius=radius, angle=-90, cross_section=xs)
    top_bend2.connect('o1', top_rect.ports['o1'])
    top_bend2.movex(length)

    top_straight = c << gf.components.straight(length=length, cross_section=xs)
    top_straight.movex(-length/2)

    top_t = gf.boolean(top_rect, top_bend1, operation='or', layer=layer)
    top_t = gf.boolean(top_t, top_bend2, operation='or', layer=layer)
    top_t = gf.boolean(top_t, top_straight, operation='or', layer=layer)

    # Create the bottom T-structure
    bottom_rect = c << gf.components.rectangle(size=(length, width), layer=layer, centered=True)
    bottom_rect.movex(-length/2)
    bottom_rect.movey(-width/2)
    
    bottom_bend1 = c << gf.components.bend_circular(radius=radius, angle=-90, cross_section=xs)
    bottom_bend1.connect('o1', bottom_rect.ports['o2'])

    bottom_bend2 = c << gf.components.bend_circular(radius=radius, angle=90, cross_section=xs)
    bottom_bend2.connect('o1', bottom_rect.ports['o1'])
    bottom_bend2.movex(length)

    bottom_straight = c << gf.components.straight(length=length, cross_section=xs)
    bottom_straight.movex(-length/2)

    bottom_t = gf.boolean(bottom_rect, bottom_bend1, operation='or', layer=layer)
    bottom_t = gf.boolean(bottom_t, bottom_bend2, operation='or', layer=layer)
    bottom_t = gf.boolean(bottom_t, bottom_straight, operation='or', layer=layer)


    # Move the bottom T-structure down
    bottom_t_ref = c << bottom_t
    bottom_t_ref.movey(-separation)

    return c

# Create and save the device
device = t_shaped_structures()
device.write_gds("t_shaped_structures.gds")

gf.show(device)