import gdsfactory as gf

@gf.cell
def create_device():
    c = gf.Component("optical_device")

    # Cross-section parameters
    width = 0.5  # Reduced width to better fit the footprint
    xs = gf.cross_section.cross_section(width=width, layer=(1, 0))

    # Parameters for the entire structure
    num_bars = 5
    bar_length = 100  # Length of each bar
    bar_spacing = 1  # Reduced bar spacing to better fit in the footprint
    vertical_length = 1 # Vertical section length
    
    # Total vertical offset from center of the bar structure
    vertical_offset = (num_bars - 1) / 2 * bar_spacing + vertical_length

    # Loop to create the horizontal bars
    for i in range(num_bars):
        y_offset = (i - (num_bars - 1) / 2) * bar_spacing  # Calculate the y offset for the bar
        bar = c << gf.components.straight(length=bar_length, cross_section=xs) # create bars
        bar.movey(y_offset)
        bar.movex(-bar_length/2)

    #Create vertical sections
    #Top Section
    top_straight = c << gf.components.straight(length=vertical_length, cross_section=xs)
    top_straight.movex(-bar_length/2)
    top_straight.movey(vertical_offset)
    top_straight.rotate(angle = -90)
    
    top_straight2 = c << gf.components.straight(length=vertical_length, cross_section=xs)
    top_straight2.movex(bar_length/2)
    top_straight2.movey(vertical_offset)
    top_straight2.rotate(angle = -90)

    #Bottom Section
    bottom_straight = c << gf.components.straight(length=vertical_length, cross_section=xs)
    bottom_straight.movex(-bar_length/2)
    bottom_straight.movey(-vertical_offset)
    bottom_straight.rotate(angle = -90)
    
    bottom_straight2 = c << gf.components.straight(length=vertical_length, cross_section=xs)
    bottom_straight2.movex(bar_length/2)
    bottom_straight2.movey(-vertical_offset)
    bottom_straight2.rotate(angle = -90)

    #Connect to the top bar
    top_bar_x = -bar_length/2 + vertical_length
    
    # Connect top straight sections to the top bars.
    # Extrude each bar segment of defined length for each number of bars.
    for i in range(num_bars):
        y_offset = (i - (num_bars - 1) / 2) * bar_spacing + vertical_length  # Calculate the y offset for the bar
        left_straight = c << gf.components.straight(length=vertical_length, cross_section=xs) # create bars
        left_straight.movex(-bar_length/2)
        left_straight.movey(y_offset)

        right_straight = c << gf.components.straight(length=vertical_length, cross_section=xs) # create bars
        right_straight.movex(bar_length/2 - vertical_length) # bar length / 2 - end length
        right_straight.movey(y_offset)
    
        #connect bottom section to top bars
        y_offset_bottom = (i - (num_bars - 1) / 2) * bar_spacing - vertical_length  # Calculate the y offset for the bar
        left_straight_bottom = c << gf.components.straight(length=vertical_length, cross_section=xs) # create bars
        left_straight_bottom.movex(-bar_length/2)
        left_straight_bottom.movey(y_offset_bottom)

        right_straight_bottom = c << gf.components.straight(length=vertical_length, cross_section=xs) # create bars
        right_straight_bottom.movex(bar_length/2 - vertical_length) # bar length / 2 - end length
        right_straight_bottom.movey(y_offset_bottom)


    return c

device = create_device()
device.write_gds("optical_device.gds")
device.show()