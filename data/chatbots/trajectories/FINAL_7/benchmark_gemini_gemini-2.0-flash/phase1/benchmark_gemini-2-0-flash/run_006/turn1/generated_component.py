import gdsfactory as gf

@gf.cell
def my_device():
    c = gf.Component()

    # Define cross section
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))

    # Outer Oval
    outer_radius = 2.75  # Approximate oval radius
    outer_oval = c << gf.components.ellipse(radii=(outer_radius, outer_radius), layer=(1, 0))

    # Central Structure
    central_width = 0.5
    central_length = 1.5

    # top section
    top_straight = c << gf.components.straight(length=central_length, cross_section=xs)
    top_square = c << gf.components.rectangle(size=(0.5, 0.5), layer=(1, 0))

    top_square.movex(-1.0)
    top_square.movey(1.0)
    top_straight.movey(1.0)

    top_square2 = c << gf.components.rectangle(size=(0.5, 0.5), layer=(1, 0))

    top_square2.movex(0.5)
    top_square2.movey(1.0)

    # bottom section
    bot_straight = c << gf.components.straight(length=central_length, cross_section=xs)
    bot_square = c << gf.components.rectangle(size=(0.5, 0.5), layer=(1, 0))
    bot_square.movex(-1.0)
    bot_square.movey(-1.0)

    bot_square2 = c << gf.components.rectangle(size=(0.5, 0.5), layer=(1, 0))
    bot_square2.movex(0.5)
    bot_square2.movey(-1.0)

    outer_straight_length = 0.5
    outer_straight_top = c << gf.components.straight(length=outer_straight_length, cross_section=xs)
    outer_straight_bot = c << gf.components.straight(length=outer_straight_length, cross_section=xs)

    outer_straight_top.movex(-2.5)
    outer_straight_top.movey(0.25)
    outer_straight_bot.movex(-2.5)
    outer_straight_bot.movey(-0.25)

    # Outer Rectangle (to define footprint better) - making the oval less dominant
    outer_rect = c << gf.components.rectangle(size=(3.0, 5.5), layer=(1, 0), centered=True)


    return c

# Create and save
device = my_device()
device.write_gds("my_device.gds")
device.show()