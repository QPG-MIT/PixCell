import gdsfactory as gf
from gdsfactory.components import rectangle
from gdsfactory.components import straight

@gf.cell
def my_device():
    c = gf.Component()
    layer = (1, 0)

    # Main rectangle
    rect_width = 20
    rect_height = 8
    main_rect = c << rectangle(size=(rect_width, rect_height), layer=layer, centered=True)
    main_rect.move((-rect_width/2,-rect_height/2))

    # Bottom notch
    notch_width = 3
    notch_height = 2
    notch = c << rectangle(size=(notch_width, notch_height), layer=layer, centered=True)
    notch.move((rect_width/2-notch_width/2+0.2,-notch_height))
    # Join main rect and the notch
    main_rect = c << gf.boolean(main_rect, notch, operation="or", layer=layer)
    main_rect.move((rect_width/2-notch_width/2,notch_height/2))


    # Top rectangles
    num_rects = 4
    rect_top_width = 2
    rect_top_height = 5
    rect_top_spacing = (rect_width - num_rects * rect_top_width)/(num_rects - 1)

    x_start = 0 # First one is placed here

    for i in range(num_rects):
        top_rect = c << rectangle(size=(rect_top_width, rect_top_height), layer=layer, centered=True)
        x_pos = 0 + i*(rect_top_spacing + rect_top_width)
        top_rect.move((x_pos,-rect_top_height-rect_height))
        # Join to main rect
        main_rect = c << gf.boolean(main_rect, top_rect, operation="or", layer=layer)
        main_rect.move((-x_pos,rect_top_height+rect_height))

    return c

device = my_device()
device.show()