import gdsfactory as gf
from gdsfactory.components import rectangle


@gf.cell
def my_device():
    c = gf.Component()

    # Outer oval
    outer_oval = c.add_ref(gf.components.ellipse(radii=(1.5, 2.75), layer=(1, 0)))  # radii = (x_radius, y_radius)

    # Central rectangles
    rect1 = c.add_ref(gf.components.rectangle(size=(0.5, 0.3), layer=(1, 0), centered=True))
    rect2 = c.add_ref(gf.components.rectangle(size=(0.5, 0.3), layer=(1, 0), centered=True))
    rect1.movex(-0.5)
    rect2.movex(0.5)

    group_rect_top = gf.Component()
    group_rect_top << rect1
    group_rect_top << rect2
    group_rect_top_ref = c.add_ref(group_rect_top)
    group_rect_top_ref.movey(0.75)

    group_rect_bottom = gf.Component()
    rect1_bottom = c.add_ref(gf.components.rectangle(size=(0.5, 0.3), layer=(1, 0), centered=True))
    rect2_bottom = c.add_ref(gf.components.rectangle(size=(0.5, 0.3), layer=(1, 0), centered=True))
    rect1_bottom.movex(-0.5)
    rect2_bottom.movex(0.5)
    group_rect_bottom << rect1_bottom
    group_rect_bottom << rect2_bottom
    group_rect_bottom_ref = c.add_ref(group_rect_bottom)
    group_rect_bottom_ref.movey(-0.75)

    # Connectors
    connector_width = 0.15
    connector_horizontal_length = 0.3
    connector_diagonal_length = 0.35
    connector_vertical_length = 0.1

    # Top left connector
    connector_top_left = gf.Component()
    rect_left_top = connector_top_left << gf.components.rectangle(size=(connector_horizontal_length, connector_width), layer=(1, 0), centered=True)
    rect_left_top.movex(-connector_horizontal_length/2- 0.25)

    rect_left_diagonal_top = connector_top_left << gf.components.rectangle(size=(connector_diagonal_length, connector_width), layer=(1, 0), centered=True)
    rect_left_diagonal_top.rotate(45)
    rect_left_diagonal_top.movex(-0.7)
    rect_left_diagonal_top.movey(0.4)

    rect_left_vertical_top = connector_top_left << gf.components.rectangle(size=(connector_width, connector_vertical_length), layer=(1, 0), centered=True)
    rect_left_vertical_top.movex(-1.2)
    rect_left_vertical_top.movey(0.8)

    connector_top_left_ref = c.add_ref(connector_top_left)
    connector_top_left_ref.movex(0.01)
    connector_top_left_ref.movey(0.2)


    # Top right connector
    connector_top_right = gf.Component()
    rect_right_top = connector_top_right << gf.components.rectangle(size=(connector_horizontal_length, connector_width), layer=(1, 0), centered=True)
    rect_right_top.movex(connector_horizontal_length/2+ 0.25)

    rect_right_diagonal_top = connector_top_right << gf.components.rectangle(size=(connector_diagonal_length, connector_width), layer=(1, 0), centered=True)
    rect_right_diagonal_top.rotate(-45)
    rect_right_diagonal_top.movex(0.7)
    rect_right_diagonal_top.movey(0.4)

    rect_right_vertical_top = connector_top_right << gf.components.rectangle(size=(connector_width, connector_vertical_length), layer=(1, 0), centered=True)
    rect_right_vertical_top.movex(1.2)
    rect_right_vertical_top.movey(0.8)

    connector_top_right_ref = c.add_ref(connector_top_right)
    connector_top_right_ref.movex(-0.01)
    connector_top_right_ref.movey(0.2)

    # Bottom left connector
    connector_bottom_left = gf.Component()
    rect_left_bottom = connector_bottom_left << gf.components.rectangle(size=(connector_horizontal_length, connector_width), layer=(1, 0), centered=True)
    rect_left_bottom.movex(-connector_horizontal_length/2- 0.25)

    rect_left_diagonal_bottom = connector_bottom_left << gf.components.rectangle(size=(connector_diagonal_length, connector_width), layer=(1, 0), centered=True)
    rect_left_diagonal_bottom.rotate(-45)
    rect_left_diagonal_bottom.movex(-0.7)
    rect_left_diagonal_bottom.movey(-0.4)

    rect_left_vertical_bottom = connector_bottom_left << gf.components.rectangle(size=(connector_width, connector_vertical_length), layer=(1, 0), centered=True)
    rect_left_vertical_bottom.movex(-1.2)
    rect_left_vertical_bottom.movey(-0.8)

    connector_bottom_left_ref = c.add_ref(connector_bottom_left)
    connector_bottom_left_ref.movex(0.01)
    connector_bottom_left_ref.movey(-0.2)

    # Bottom right connector
    connector_bottom_right = gf.Component()
    rect_right_bottom = connector_bottom_right << gf.components.rectangle(size=(connector_horizontal_length, connector_width), layer=(1, 0), centered=True)
    rect_right_bottom.movex(connector_horizontal_length/2+ 0.25)

    rect_right_diagonal_bottom = connector_bottom_right << gf.components.rectangle(size=(connector_diagonal_length, connector_width), layer=(1, 0), centered=True)
    rect_right_diagonal_bottom.rotate(45)
    rect_right_diagonal_bottom.movex(0.7)
    rect_right_diagonal_bottom.movey(-0.4)

    rect_right_vertical_bottom = connector_bottom_right << gf.components.rectangle(size=(connector_width, connector_vertical_length), layer=(1, 0), centered=True)
    rect_right_vertical_bottom.movex(1.2)
    rect_right_vertical_bottom.movey(-0.8)

    connector_bottom_right_ref = c.add_ref(connector_bottom_right)
    connector_bottom_right_ref.movex(-0.01)
    connector_bottom_right_ref.movey(-0.2)

    # Boolean subtraction
    inner_group = gf.Component()
    inner_group << group_rect_top_ref
    inner_group << group_rect_bottom_ref
    inner_group << connector_top_left_ref
    inner_group << connector_top_right_ref
    inner_group << connector_bottom_left_ref
    inner_group << connector_bottom_right_ref
    result = gf.boolean(outer_oval, inner_group, operation="not", layer=(1, 0))

    return result


if __name__ == "__main__":
    c = my_device()
    c.show(show_ports=True)