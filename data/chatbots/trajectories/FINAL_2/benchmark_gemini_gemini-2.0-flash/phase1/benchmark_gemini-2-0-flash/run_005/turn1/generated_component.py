import gdsfactory as gf
from gdsfactory.components import rectangle
# from gdsfactory.components import trapezoid # Removed import as it is not used
from gdsfactory.components import straight

@gf.cell
def my_device():
    c = gf.Component("my_device")

    # Parameters
    base_width = 20  # Width of the main rectangular body
    base_height = 8  # Height of the main rectangular body
    top_extension_width = 3 # Width of each top extension
    top_extension_height = 3 # Height of each top extension
    bottom_extension_width = 2 # Width of the bottom extension
    bottom_extension_height = 2 # Height of the bottom extension
    gap = 1.5 # gap between each top_extension
    
    # Create the main rectangular body
    base = c << rectangle(size=(base_width, base_height), layer=(1, 0), centered=True)
    base.center

    # Create the top extensions
    top_ext1 = c << rectangle(size=(top_extension_width, top_extension_height), layer=(1, 0), centered=True)
    top_ext2 = c << rectangle(size=(top_extension_width, top_extension_height), layer=(1, 0), centered=True)
    top_ext3 = c << rectangle(size=(top_extension_width, top_extension_height), layer=(1, 0), centered=True)
    top_ext4 = c << rectangle(size=(top_extension_width, top_extension_height), layer=(1, 0), centered=True)

    # Position the top extensions
    x_pos = - (3*top_extension_width/2 + 3*gap/2 +top_extension_width/2)
    top_ext1.move((x_pos,base_height/2 + top_extension_height/2))
    x_pos += top_extension_width/2 + gap/2 + top_extension_width/2
    top_ext2.move((x_pos,base_height/2 + top_extension_height/2))
    x_pos += top_extension_width/2 + gap/2 + top_extension_width/2
    top_ext3.move((x_pos,base_height/2 + top_extension_height/2))
    x_pos += top_extension_width/2 + gap/2 + top_extension_width/2
    top_ext4.move((x_pos,base_height/2 + top_extension_height/2))

    # Create the bottom extension
    bottom_ext = c << rectangle(size=(bottom_extension_width, bottom_extension_height), layer=(1, 0), centered=True)
    bottom_ext.move((0, -base_height/2 - bottom_extension_height/2))

    return c

device = my_device()
device.show() # Removed show_ports=True