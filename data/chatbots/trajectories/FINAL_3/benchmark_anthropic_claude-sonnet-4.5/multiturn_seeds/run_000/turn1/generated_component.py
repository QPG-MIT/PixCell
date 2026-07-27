import gdsfactory as gf

@gf.cell
def create_device():
    """
    Creates a waveguide crossing structure with two S-bend waveguides.
    The top and bottom waveguides curve toward each other in the center
    and then curve back to their original positions.
    """
    c = gf.Component()
    
    # Define cross-section for waveguides
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # Device parameters
    total_length = 120  # Total device length in um
    total_height = 4    # Total device height in um
    
    # Vertical offset (distance from center to each waveguide)
    y_offset = 1.5  # Each waveguide is 1.5 um from center
    
    # S-bend parameters
    s_bend_length = 30  # Horizontal length of each S-bend
    straight_length = 30  # Length of straight sections on each end
    
    # TOP WAVEGUIDE
    # Start straight section
    top_straight1 = c << gf.components.straight(length=straight_length, cross_section=xs)
    top_straight1.movey(y_offset)
    
    # First S-bend: curves down toward center
    top_s1 = c << gf.components.bend_s(size=(s_bend_length, -y_offset), cross_section=xs)
    top_s1.connect("o1", top_straight1.ports["o2"])
    
    # Second S-bend: curves back up to original height
    top_s2 = c << gf.components.bend_s(size=(s_bend_length, y_offset), cross_section=xs)
    top_s2.connect("o1", top_s1.ports["o2"])
    
    # End straight section
    top_straight2 = c << gf.components.straight(length=straight_length, cross_section=xs)
    top_straight2.connect("o1", top_s2.ports["o2"])
    
    # BOTTOM WAVEGUIDE
    # Start straight section
    bottom_straight1 = c << gf.components.straight(length=straight_length, cross_section=xs)
    bottom_straight1.movey(-y_offset)
    
    # First S-bend: curves up toward center
    bottom_s1 = c << gf.components.bend_s(size=(s_bend_length, y_offset), cross_section=xs)
    bottom_s1.connect("o1", bottom_straight1.ports["o2"])
    
    # Second S-bend: curves back down to original height
    bottom_s2 = c << gf.components.bend_s(size=(s_bend_length, -y_offset), cross_section=xs)
    bottom_s2.connect("o1", bottom_s1.ports["o2"])
    
    # End straight section
    bottom_straight2 = c << gf.components.straight(length=straight_length, cross_section=xs)
    bottom_straight2.connect("o1", bottom_s2.ports["o2"])
    
    return c

# Create the device and save to GDS
device = create_device()
device.write_gds("waveguide_crossing.gds")

# Optional: display the device
device.show()