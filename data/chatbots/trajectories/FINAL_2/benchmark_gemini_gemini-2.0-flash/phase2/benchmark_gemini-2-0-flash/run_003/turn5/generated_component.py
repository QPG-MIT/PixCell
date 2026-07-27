import gdsfactory as gf

@gf.cell
def my_device():
    c = gf.Component()
    layer = (1, 0)

    # Main rectangle
    main_rect = c << gf.components.rectangle(size=(25, 7), layer=layer, centered=True)

    # Bottom extension
    bottom_extension_width = 3
    bottom_extension_height = 3
    bottom_extension = c << gf.components.rectangle(size=(bottom_extension_width, bottom_extension_height), layer=layer, centered=True)
    bottom_extension.move( (0, -4.5) ) # shift it down

    # Four top extensions (trapezoids)
    top_extension_base_width = 4 #original code's width
    top_extension_top_width = 2  # original code's top extension width
    top_extension_height = 3  # original code's height
    num_extensions = 4

    # Calculate x positions
    total_base_width = num_extensions * top_extension_base_width
    total_spacing_width = 25 - total_base_width
    spacing = total_spacing_width / (num_extensions + 1)

    x_positions = []
    current_x = -12.5 + spacing + top_extension_base_width/2
    for _ in range(num_extensions):
        x_positions.append(current_x)
        current_x += top_extension_base_width + spacing
    
    for x in x_positions:
        # Replace rectangle with taper for trapezoid shape
        top_extension = c << gf.components.taper(length=top_extension_height, width1=top_extension_base_width, width2=top_extension_top_width)

        # move to the right position
        top_extension.move((x - top_extension_base_width/2, 3.5))

    return c

device = my_device()
device.show()
device.write_gds("my_device.gds")