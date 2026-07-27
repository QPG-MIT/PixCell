import gdsfactory as gf
from gdsfactory.components import rectangle
from gdsfactory.components import triangle

@gf.cell
def device():
    c = gf.Component("device")
    
    # Base rectangle dimensions
    rect_width = 20
    rect_height = 10
    
    # Triangle dimensions
    triangle_base = 5
    triangle_height = 7
    
    # Spacing between triangles
    triangle_spacing = 8
    
    # Create the base rectangle
    rect = c << rectangle(size=(rect_width, rect_height), layer=(1, 0))
    rect.movex(-rect_width/2)
    rect.movey(-rect_height/2)
    
    # Create the triangles
    triangle1 = c << triangle(x=triangle_base, y=triangle_height, layer=(1, 0))
    triangle1.rotate(angle=90)
    triangle1.movex(rect_width/2 + triangle_spacing)
    triangle1.movey(rect_height/2 - triangle_base)
    
    triangle2 = c << triangle(x=triangle_base, y=triangle_height, layer=(1, 0))
    triangle2.rotate(angle=90)
    triangle2.movex(rect_width/2 + triangle_spacing + triangle_spacing/2)
    triangle2.movey(rect_height/2 - triangle_base)

    
    return c

# Create and save
device = device()
device.show()
device.write_gds("device.gds")