import gdsfactory as gf
from gdsfactory.components import rectangle
from gdsfactory.components import ellipse


@gf.cell(check_instances=False)
def recreate_image():
    """Recreates the provided image using GDSFactory."""
    c = gf.Component("recreate_image")

    # Outer oval
    oval = c << ellipse(radii=(15, 5), layer=(1, 0))

    # Central rectangles (2 per side)
    rect1 = c << rectangle(size=(2, 1), layer=(1, 0), centered=True)
    rect2 = c << rectangle(size=(2, 1), layer=(1, 0), centered=True)
    rect3 = c << rectangle(size=(2, 1), layer=(1, 0), centered=True)
    rect4 = c << rectangle(size=(2, 1), layer=(1, 0), centered=True)

    rect1.move((5, 1.5))
    rect2.move((9, 1.5))
    rect3.move((-5, -1.5))
    rect4.move((-9, -1.5))


    # Horizontal segments
    h_seg1 = c << rectangle(size=(4, 0.5), layer=(1, 0), centered=True)
    h_seg2 = c << rectangle(size=(4, 0.5), layer=(1, 0), centered=True)

    h_seg1.move((1, 1.5))
    h_seg2.move((-1, -1.5))

    # Angled segments
    angled_seg1 = c << rectangle(size=(3, 0.5), layer=(1, 0), centered=True)
    angled_seg2 = c << rectangle(size=(3, 0.5), layer=(1, 0), centered=True)
    angled_seg3 = c << rectangle(size=(3, 0.5), layer=(1, 0), centered=True)
    angled_seg4 = c << rectangle(size=(3, 0.5), layer=(1, 0), centered=True)

    angled_seg1.rotate(45)
    angled_seg2.rotate(-45)
    angled_seg3.rotate(45)
    angled_seg4.rotate(-45)

    angled_seg1.move((11, 3.5))
    angled_seg2.move((11, -3.5))
    angled_seg3.move((-11, 3.5))
    angled_seg4.move((-11, -3.5))
    
    #Central section of geometry
    central_rect = c << rectangle(size=(4, 1), layer=(1, 0), centered=True)
    central_rect_top = c << rectangle(size=(4, 1), layer=(1, 0), centered=True)
    
    central_rect.move((13.5, 0))
    central_rect_top.move((-13.5, 0))
    
    
    # Vertical segments to the oval
    vertical_seg1 = c << rectangle(size=(0.5, 3), layer=(1, 0), centered=True)
    vertical_seg2 = c << rectangle(size=(0.5, 3), layer=(1, 0), centered=True)
    vertical_seg3 = c << rectangle(size=(0.5, 3), layer=(1, 0), centered=True)
    vertical_seg4 = c << rectangle(size=(0.5, 3), layer=(1, 0), centered=True)
    
    vertical_seg1.move((15, 2.75))
    vertical_seg2.move((15, -2.75))
    vertical_seg3.move((-15, 2.75))
    vertical_seg4.move((-15, -2.75))

    return c

if __name__ == "__main__":
    c = recreate_image()
    c.show()