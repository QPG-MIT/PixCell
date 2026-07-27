import gdsfactory as gf
from gdsfactory import Component
from gdsfactory.cross_section import CrossSection


@gf.cell
def my_fork_splitter(radius_min: float = 10.0) -> Component:
    """
    Recreates the fork splitter geometry using GDSFactory parametric functions.
    """
    c = gf.Component("fork_splitter")

    # Define waveguide cross-section
    xs = gf.cross_section.cross_section(width=1, layer=(1, 0), radius=radius_min)

    # Main waveguide
    straight_length = 5  # Adjust as needed
    straight = c << gf.components.straight(length=straight_length, cross_section=xs)

    # Taper lengths
    taper_length = 10  # Adjust as needed
    taper_width1 = xs.width #1
    taper_width2 = 2 * xs.width#1.5  # Adjust as needed

    # Splitter arms
    splitter_arm_length = 15  # Adjust as needed

    # Gap between splitter arms
    gap = 0.2 # Adjust as needed

    # Middle waveguide (straight)
    middle_wg = c << gf.components.straight(length=splitter_arm_length + taper_length + straight_length, cross_section=xs)
    middle_wg.movex(-5) # shift to the left so that the straight section is at the left edge of the component
    
    # Upper arm
    upper_taper = c << gf.components.taper(length=taper_length, width1=taper_width1, width2=taper_width2)
    upper_bend = c << gf.components.bend_euler(radius=radius_min, angle=30, cross_section=xs)  # Adjust radius and angle as needed
    upper_straight = c << gf.components.straight(length=splitter_arm_length, cross_section=xs)

    upper_arm_width_diff = (taper_width2 - taper_width1)/2 + gap/2
    upper_taper.connect("o1", straight.ports["o2"])
    upper_taper.movey(upper_arm_width_diff)
    
    upper_bend.connect("o1", upper_taper.ports["o2"])
    upper_straight.connect("o1", upper_bend.ports["o2"])
    
    # Lower arm
    lower_taper = c << gf.components.taper(length=taper_length, width1=taper_width1, width2=taper_width2)
    lower_bend = c << gf.components.bend_euler(radius=radius_min, angle=-30, cross_section=xs) # Adjust radius and angle as needed
    lower_straight = c << gf.components.straight(length=splitter_arm_length, cross_section=xs)

    lower_taper.connect("o1", straight.ports["o2"])
    lower_taper.movey(-upper_arm_width_diff)
    
    lower_bend.connect("o1", lower_taper.ports["o2"])
    lower_straight.connect("o1", lower_bend.ports["o2"])
    
    #Add ports
    c.add_port("o1", port=straight.ports["o1"])
    c.add_port("o2", port=upper_straight.ports["o2"])
    c.add_port("o3", port=middle_wg.ports["o2"])
    c.add_port("o4", port=lower_straight.ports["o2"])
    
    return c

if __name__ == "__main__":
    splitter = my_fork_splitter()
    splitter.show(show_ports=True)