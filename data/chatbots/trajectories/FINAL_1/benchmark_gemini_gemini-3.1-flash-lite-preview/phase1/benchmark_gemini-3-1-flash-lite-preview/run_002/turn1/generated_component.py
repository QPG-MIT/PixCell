import gdsfactory as gf

@gf.cell
def create_tapered_splitter():
    # 1. Initialize component
    c = gf.Component("tapered_splitter")
    
    # Define a cross section
    xs = gf.cross_section.cross_section(width=0.3, layer=(1, 0))
    
    # 2. Central Spike (using a taper component)
    # Tapers from 0.5um to 0.05um over 20um length
    spike = c << gf.components.taper(
        length=20, 
        width1=0.5, 
        width2=0.05, 
        cross_section=xs
    )
    # Align the spike to the start of the device
    spike.movex(0)
    
    # 3. Outer Arms
    # Each arm consists of a straight section followed by an Euler bend
    arm_straight_len = 15
    bend_radius = 20
    
    # Top Arm
    top_straight = c << gf.components.straight(length=arm_straight_len, cross_section=xs)
    top_bend = c << gf.components.bend_euler(radius=bend_radius, angle=10, cross_section=xs)
    
    # Connect top arm components
    top_bend.connect("o1", top_straight.ports["o2"])
    
    # Position top arm (Offset vertically to fit 1.7um footprint)
    top_straight.movey(0.6)
    top_bend.movey(0.6)
    
    # Bottom Arm (Mirror of top)
    bot_straight = c << gf.components.straight(length=arm_straight_len, cross_section=xs)
    bot_bend = c << gf.components.bend_euler(radius=bend_radius, angle=-10, cross_section=xs)
    
    # Connect bottom arm components
    bot_bend.connect("o1", bot_straight.ports["o2"])
    
    # Position bottom arm
    bot_straight.movey(-0.6)
    bot_bend.movey(-0.6)
    
    return c

# 4. Generate and Save
# This explicitly creates the component and writes it to a file
device = create_tapered_splitter()
device.write_gds("tapered_splitter.gds")

print("GDS file 'tapered_splitter.gds' successfully created.")