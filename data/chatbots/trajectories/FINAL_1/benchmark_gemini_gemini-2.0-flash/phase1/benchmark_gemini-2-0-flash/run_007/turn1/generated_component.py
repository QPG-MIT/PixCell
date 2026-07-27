import gdsfactory as gf
from gdsfactory.components import taper
from gdsfactory.components import straight
from gdsfactory.components import bend_euler

@gf.cell
def my_device():
    c = gf.Component("splitter")

    # Parameters
    length_taper = 15
    width_wg = 1
    width_taper_narrow = 0.2
    length_straight = 5
    radius_bend = 5

    # 1. Middle Straight Waveguide
    xs_narrow = gf.cross_section.cross_section(width=width_taper_narrow)
    xs_wide = gf.cross_section.cross_section(width=width_wg)
    wg_mid = c << straight(length=length_straight, cross_section=xs_narrow)
    
    # 2. Top and Bottom Straight Waveguides and Tapers
    wg_top1 = c << straight(length=length_taper, cross_section=xs_wide)
    wg_bot1 = c << straight(length=length_taper, cross_section=xs_wide)

    taper_top = c << taper(length=length_taper, width1=width_taper_narrow, width2=width_wg)
    taper_bot = c << taper(length=length_taper, width1=width_taper_narrow, width2=width_wg)

    # Align the Tapers and Straights
    taper_top.connect("o1", wg_mid.ports["o2"])
    taper_bot.connect("o1", wg_mid.ports["o1"])

    # Move the Straights after the tapers 
    wg_top1.connect("o1", taper_top.ports["o2"])
    wg_bot1.connect("o1", taper_bot.ports["o2"])

    #Create Bend parameters and connect 
    bend_top = c << bend_euler(radius=radius_bend, angle = 90, cross_section=xs_wide)
    bend_bot = c << bend_euler(radius=radius_bend, angle = -90, cross_section=xs_wide)

    bend_top.connect("o1", wg_top1.ports["o2"])
    bend_bot.connect("o1", wg_bot1.ports["o2"])

    straight_out_top = c << straight(length = 10, cross_section=xs_wide)
    straight_out_bot = c << straight(length = 10, cross_section=xs_wide)

    straight_out_top.connect("o1", bend_top.ports["o2"])
    straight_out_bot.connect("o1", bend_bot.ports["o2"])

    #Add external ports
    c.add_port("o1", port=straight_out_top.ports["o2"])
    c.add_port("o2", port=wg_mid.ports["o3"])
    c.add_port("o3", port=straight_out_bot.ports["o2"])


    return c

# Create and save
device = my_device()
device.show(show_ports=True)
device.write_gds("my_device.gds")