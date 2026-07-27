import gdsfactory as gf

@gf.cell
def create_device():
    c = gf.Component()
    
    # Parameters
    # We use a slightly thicker width for the rails to create visual contrast
    rail_width = 1.0
    line_width = 0.4
    bar_length = 80.0
    pitch = 4.0
    bend_radius = 15.0
    rail_straight_length = 10.0 # Vertical straight segment between bends
    
    # Cross sections
    xs_rail = gf.cross_section.cross_section(width=rail_width, layer=(1, 0))
    xs_line = gf.cross_section.cross_section(width=line_width, layer=(1, 0))
    
    # 1. Create the Central Stack (5 lines)
    for i in range(5):
        y_pos = (i - 2) * pitch
        line = c << gf.components.straight(length=bar_length, cross_section=xs_line)
        line.movey(y_pos)
        
    # 2. Construct the Bracket Side Rails
    # We need a left and right bracket. Let's make a function for one side.
    @gf.cell
    def create_bracket(mirror=False):
        b = gf.Component()
        
        # Bottom bend
        bot = b << gf.components.bend_euler(radius=bend_radius, angle=90, cross_section=xs_rail)
        
        # Straight vertical part
        vert = b << gf.components.straight(length=rail_straight_length, cross_section=xs_rail)
        vert.connect("o1", bot.ports["o2"])
        
        # Top bend
        top = b << gf.components.bend_euler(radius=bend_radius, angle=90, cross_section=xs_rail)
        top.connect("o1", vert.ports["o2"])
        
        # Add ports to the bracket ends for easy alignment
        b.add_port("bottom", port=bot.ports["o1"])
        b.add_port("top", port=top.ports["o2"])
        
        # Rotate/Mirror if needed
        if mirror:
            b.mirror(p1=(0,0), p2=(0,1))
            
        return b

    # 3. Assemble the brackets around the center
    # Left bracket
    left_bracket = c << create_bracket(mirror=False)
    # Position: Align the center of the vertical straight part with the center of the stack
    left_bracket.movex(-(bar_length / 2 + bend_radius))
    left_bracket.movey(-(rail_straight_length / 2 + bend_radius))
    
    # Right bracket
    right_bracket = c << create_bracket(mirror=True)
    right_bracket.movex((bar_length / 2 + bend_radius))
    right_bracket.movey(-(rail_straight_length / 2 + bend_radius))
    
    c.flatten()
    return c

if __name__ == "__main__":
    c = create_device()
    c.write_gds("device_curved.gds")
    # c.show() # Uncomment to open in KLayout