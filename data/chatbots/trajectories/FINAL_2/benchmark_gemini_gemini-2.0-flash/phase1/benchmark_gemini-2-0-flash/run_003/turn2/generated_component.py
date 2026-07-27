import gdsfactory as gf

@gf.cell
def my_device():
    c = gf.Component()
    layer = (1, 0)

    # Main rectangle
    main_rect = c << gf.components.rectangle(size=(25, 7), layer=layer, centered=True)

    # Bottom extension
    bottom_extension = c << gf.components.rectangle(size=(3, 3), layer=layer, centered=True)
    bottom_extension.move( (0, -5) ) # shift it down to desired position

    # Four top extensions (assuming equal spacing)
    top_extension_width = 2
    top_extension_height = 3
    top_extension_base_width = 4

    # Calculate x positions
    spacing = (25 - 4*top_extension_base_width)/5 # spacing between top extentions
    x_positions = [-12.5 + top_extension_base_width/2 + spacing, -12.5 + 3*top_extension_base_width/2 + 2*spacing , -12.5 + 5*top_extension_base_width/2 + 3*spacing , -12.5 + 7*top_extension_base_width/2 + 4*spacing]

    for x in x_positions:
        # use taper for top extension
        top_extension = c << gf.components.taper(length=top_extension_height, width1=top_extension_base_width, width2=top_extension_width)

        top_extension.move((x-top_extension_base_width/2 + top_extension_width/2, 5-top_extension_height/2))

    return c

device = my_device()
device.show()
device.write_gds("my_device.gds")