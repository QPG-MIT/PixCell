import gdsfactory as gf

@gf.cell
def tapered_waveguide_system():
    c = gf.Component()
    
    # 1. Define standard cross section
    # Using a 0.2um wide waveguide, which is typical for these structures
    xs = gf.cross_section.cross_section(width=0.2, layer=(1, 0))
    
    # 2. Define the Central Taper
    # The center is a wedge/taper that widens across the 40um length
    # Note: width1=0.1 to width2=0.8 creates the pointed look
    center_taper = c << gf.components.taper(
        length=40, 
        width1=0.1, 
        width2=0.8, 
        cross_section=xs
    )
    
    # 3. Define Outer Waveguides (using S-bends)
    # To fit the 1.7um footprint, we divide the 40um length into:
    # - 10um straight start
    # - 20um S-bend (transition)
    # - 10um straight end
    # S-bend dy=0.3 moves the waveguide vertically to follow the taper
    bend_params = {"size": (20, 0.3), "cross_section": xs}
    
    # Create Top Arm
    top_in = c << gf.components.straight(length=10, cross_section=xs)
    top_bend = c << gf.components.bend_s(**bend_params)
    top_out = c << gf.components.straight(length=10, cross_section=xs)
    
    # Create Bottom Arm
    bot_in = c << gf.components.straight(length=10, cross_section=xs)
    bot_bend = c << gf.components.bend_s(**bend_params)
    bot_out = c << gf.components.straight(length=10, cross_section=xs)
    
    # 4. Position and Connect
    # Place center at Y=0
    center_taper.movey(0)
    
    # Position Top Arm (approx 0.5um above center)
    top_in.move((0, 0.5))
    top_bend.connect("o1", top_in.ports["o2"])
    top_out.connect("o1", top_bend.ports["o2"])
    
    # Position Bottom Arm (approx 0.5um below center)
    bot_in.move((0, -0.5))
    bot_bend.connect("o1", bot_in.ports["o2"])
    bot_out.connect("o1", bot_bend.ports["o2"])
    
    return c

# Generate the component
device = tapered_waveguide_system()
device.write_gds("tapered_device.gds")
device.show()