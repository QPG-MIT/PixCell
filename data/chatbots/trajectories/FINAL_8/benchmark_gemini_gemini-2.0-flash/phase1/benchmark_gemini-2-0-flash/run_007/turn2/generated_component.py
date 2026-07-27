import gdsfactory as gf
from gdsfactory.components import rectangle

@gf.cell
def my_device(rect_width=5, rect_height=10):
    c = gf.Component("my_device")

    # Create a rectangle
    rect = c << rectangle(size=(rect_width, rect_height))
    rect.movex(-rect_width/2) #move the center to x=0
    rect.movey(-rect_height/2) #move the center to y=0

    return c

device = my_device()
device.show()
device.write_gds("my_device.gds")