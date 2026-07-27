import gdsfactory as gf
from gdsfactory.component import Component

@gf.cell
def recreate_image() -> Component:
    """Recreates the geometry from the attached PNG image using GDSFactory."""
    c = gf.Component("recreated_image")

    # Define the cross-section
    width = 0.7  # Width of the waveguide
    radius_min = 5  # Minimum bend radius
    xs = gf.cross_section.cross_section(width=width, layer=(1, 0), radius=radius_min)
    
    # Horizontal Straight Segment Width
    horizontal_straight_width = 0.3  # Width of the horizontal straight segment
    
    # Length of the Horizontal Straight Segment
    horizontal_straight_length = 18.24

    # Define the length of the grating section (including the gaps)
    grating_length = 12 # Estimate visually

    # Define the number of periods in the grating
    num_periods = 32 # Counting

    # Calculate the period of the grating
    period = grating_length / num_periods

    # Calculate the width of the grating teeth (assuming 50% duty cycle)
    tooth_width = period * 0.5

    # Grating definition
    grating = gf.components.straight(length=tooth_width, cross_section=xs)
    
    # 1. Top U-Shaped Structure

    # Straight section after the bend
    straight_length = 5 # Experimentally determined

    # Top straight section
    top_straight = c << gf.components.straight(length=straight_length, cross_section=xs)
    top_straight.movex(grating_length)
    top_straight.movey(3*width)
    
    # Circular bend 
    bend_radius = radius_min # Visually determined.
    bend = c << gf.components.bend_circular(radius=bend_radius, angle=90, cross_section=xs)
    bend.connect("o1", top_straight.ports["o2"])
    
    # Top Horizontal Grating Structure
    top_grating_group = [] # List to store the grating components

    # Create and position each grating component
    for i in range(num_periods):
        grating_instance = c << grating
        grating_instance.movex(i * period)
        grating_instance.movey(3*width)
        top_grating_group.append(grating_instance)
        
    # Connect the bend to the grating start
    bend_start = c << gf.components.bend_circular(radius=bend_radius, angle=90, cross_section=xs)
    bend_start.connect("o2", top_grating_group[0].ports["o1"])
    bend_start.rotate(angle=180) # rotate the start bend
    
    # Taper at the end of U shape.
    taper_len = 2.5
    taper_width = 1
    top_taper = c << gf.components.taper(length=taper_len, width1=width, width2=taper_width)
    top_taper.connect("o1", bend.ports["o2"])
    
    # 2. Bottom U-Shaped Structure (Mirror of the top)

    # Bottom straight section
    bottom_straight = c << gf.components.straight(length=straight_length, cross_section=xs)
    bottom_straight.movex(grating_length)
    bottom_straight.movey(-3*width)

    # Bottom circular bend
    bottom_bend = c << gf.components.bend_circular(radius=bend_radius, angle=90, cross_section=xs)
    bottom_bend.connect("o2", bottom_straight.ports["o1"]) # opposite connect to mirror effect

    # Bottom Horizontal Grating Structure
    bottom_grating_group = []  # List to store the grating components
    
    # Create and position each grating component
    for i in range(num_periods):
        grating_instance = c << grating
        grating_instance.movex(i * period)
        grating_instance.movey(-3*width)
        bottom_grating_group.append(grating_instance)

    # Connect the bend to the grating start
    bend_start_bottom = c << gf.components.bend_circular(radius=bend_radius, angle=90, cross_section=xs)
    bend_start_bottom.connect("o2", bottom_grating_group[0].ports["o1"])
    bend_start_bottom.rotate(angle=180) # rotate the start bend
    bend_start_bottom.mirror()
    
    # Taper at the end of U shape.
    bottom_taper = c << gf.components.taper(length=taper_len, width1=width, width2=taper_width)
    bottom_taper.connect("o1", bottom_bend.ports["o1"])
    bottom_taper.mirror()
    
    # 3. Central Horizontal Bar

    central_bar = c << gf.components.straight(length=horizontal_straight_length, cross_section=gf.cross_section.cross_section(width=horizontal_straight_width, layer=(1, 0)))
    central_bar.movey(0)
    
    # 4. Central Gratings Group

    central_gratings_group = []  # List to store the grating components
    
    # Create and position each grating component
    for i in range(num_periods):
        grating_instance = c << grating
        grating_instance.movex(i * period)
        central_gratings_group.append(grating_instance)

    return c

if __name__ == "__main__":
    recreated_device = recreate_image()
    recreated_device.show()