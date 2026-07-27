import gdsfactory as gf
from gdsfactory.components import rectangle
from gdsfactory.components import taper
from gdsfactory.components import straight

@gf.cell
def recreate_device():
    c = gf.Component("recreated_device")

    # Main waveguide (vertical)
    main_width = 1.0  # Adjust as needed (constant width now)
    main_length = 10   # Adjust as needed

    # Taper at the top and bottom
    taper_length = 3
    taper_width1 = 0.5  # Width at the narrow end of the taper
    taper_width2 = main_width  # Width at the wide end of the taper

    # Top Taper
    taper_top = c << taper(length=taper_length, width1=taper_width1, width2=taper_width2)
    taper_top.rotate(90)
    taper_top.movex(-taper_width1/2)

    # Main Waveguide
    main_waveguide = c << straight(length=main_length, width=main_width)
    main_waveguide.movey(taper_length) # Shift main waveguide up
    main_waveguide.connect("o1", taper_top.ports["o2"])

    # Bottom Taper
    taper_bottom = c << taper(length=taper_length, width1=taper_width1, width2=taper_width2)
    taper_bottom.rotate(90)
    taper_bottom.rotate(180)
    taper_bottom.movex(taper_width1/2)
    main_waveguide.movey(-taper_length) # Shift main waveguide down
    taper_bottom.connect("o1", main_waveguide.ports["o2"])

    # Top Rectangle (Square)
    rect_size = 1.0 # Adjust as needed
    rect_top = c << rectangle(size=(rect_size, rect_size), centered=True)
    rect_top.move((main_width/2 + rect_size/2 + 0.5, main_length/2 + rect_size + 3 + taper_length)) #Position and size based on main_length, width
    rect_top.rotate(90)

    # Bottom Rectangle (Square)
    rect_bottom = c << rectangle(size=(rect_size, rect_size), centered=True)
    rect_bottom.move((main_width/2 + rect_size/2 + 0.5, -main_length/2 - rect_size - 3 - taper_length))
    rect_bottom.rotate(90)

    return c

if __name__ == "__main__":
    device = recreate_device()
    device.write_gds("recreated_device.gds")
    device.show()