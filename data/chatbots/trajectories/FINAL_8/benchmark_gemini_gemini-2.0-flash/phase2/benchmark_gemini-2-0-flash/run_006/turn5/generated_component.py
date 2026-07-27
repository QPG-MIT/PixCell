import gdsfactory as gf

@gf.cell
def my_device(num_wg=5, wg_width=0.5, wg_spacing=0.5, bend_radius=10, straight_length=100):
    c = gf.Component()
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0), radius=bend_radius) # define cross section
    
    y_offset_start = -(num_wg - 1) * (wg_width + wg_spacing) / 2  # Center vertically

    for i in range(num_wg):
        y_offset = y_offset_start + i * (wg_width + wg_spacing)

        # Create bend and straight segments
        bend1 = gf.components.bend_euler(radius=bend_radius, angle=90, cross_section=xs)
        bend2 = gf.components.bend_euler(radius=bend_radius, angle=-90, cross_section=xs)
        straight = gf.components.straight(length=straight_length, cross_section=xs)

        # Rotate second bend to create U-turn
        bend2_rotated = c << bend2
        bend2_rotated.rotate(180)

        # Place and connect components
        bend1_ref = c << bend1
        straight_ref = c << straight
        

        straight_ref.connect("o1", bend1_ref.ports["o2"]) # Straight to bend1
        bend2_rotated.connect("o1", straight_ref.ports["o2"]) # bend2 to straight

        # Move segments into position
        bend1_ref.movex(-straight_length / 2)
        bend2_rotated.movex(straight_length / 2)

        # Align the bends vertically
        bend1_ref.movey(y_offset)
        straight_ref.movey(y_offset)
        bend2_rotated.movey(y_offset)

        c.add_port(f"o1_{i}", port=bend1_ref.ports["o1"])
        c.add_port(f"o2_{i}", port=bend2_rotated.ports["o2"])

    c.flatten()
    return c

# Parameters adjusted to make the footprint 120x4
device = my_device(num_wg=5, wg_width=0.5, wg_spacing=0.5, straight_length=110, bend_radius=10)
device.show()
device.write_gds("my_device.gds")