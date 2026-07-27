import gdsfactory as gf

@gf.cell
def create_device():
    c = gf.Component("optical_device")

    # Cross-section parameters
    xs = gf.cross_section.cross_section(width=10, layer=(1, 0))

    # Horizontal bars
    num_bars = 5  # Number of horizontal bars
    spacing = 20   # Spacing between bars

    for i in range(num_bars):
        y_offset = (i - (num_bars - 1) / 2) * spacing
        bar = c << gf.components.straight(length=100, cross_section=xs)
        bar.movey(y_offset)
        bar.movex(-50) # center around (0,0)

    return c

device = create_device()
device.write_gds("optical_device.gds")
device.show()