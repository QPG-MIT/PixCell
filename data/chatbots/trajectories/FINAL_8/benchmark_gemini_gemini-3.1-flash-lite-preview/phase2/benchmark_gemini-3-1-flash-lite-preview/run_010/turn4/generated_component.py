import gdsfactory as gf

@gf.cell
def create_bracket(xs_rail):
    # Construct a C-shape using the Path API
    # 1. Start with a horizontal tip (pointing inward)
    # 2. Turn 90 degrees to form the vertical rail
    # 3. Turn 90 degrees to form the bottom horizontal tip
    
    # Path coordinates:
    # We want a vertical rail of length 20, centered at y=0.
    # The tips should extend inward (to the right).
    
    p = gf.Path()
    # Top tip
    p.append(gf.path.straight(length=10))
    # Top curve (90-degree turn)
    p.append(gf.path.arc(radius=10, angle=-90))
    # Vertical rail
    p.append(gf.path.straight(length=20))
    # Bottom curve (90-degree turn)
    p.append(gf.path.arc(radius=10, angle=-90))
    # Bottom tip
    p.append(gf.path.straight(length=10))
    
    # Extrude the path into a component
    bracket = gf.path.extrude(p, cross_section=xs_rail)
    return bracket

@gf.cell
def create_device():
    c = gf.Component()
    
    # Parameters
    rail_width = 1.2
    line_width = 0.5
    bar_length = 60.0
    pitch = 4.0
    
    # Cross sections
    xs_rail = gf.cross_section.cross_section(width=rail_width, layer=(1, 0))
    xs_line = gf.cross_section.cross_section(width=line_width, layer=(1, 0))
    
    # 1. Create the Central Stack (5 lines)
    # Pitch = 4.0, 5 lines -> y range = -8, -4, 0, 4, 8
    for i in range(5):
        y_pos = (i - 2) * pitch
        line = c << gf.components.straight(length=bar_length, cross_section=xs_line)
        line.movey(y_pos)
        # Center the line on x=0
        line.movex(-bar_length / 2)
        
    # 2. Construct and place the brackets
    left_bracket = c << create_bracket(xs_rail)
    right_bracket = c << create_bracket(xs_rail)
    
    # Position the brackets
    # The left bracket needs to be at x < -bar_length/2
    # The right bracket needs to be at x > bar_length/2 and mirrored
    
    # Align left bracket (its tips point right, so we need to flip it horizontally or just position it)
    # The path was constructed to face right.
    left_bracket.movex(-bar_length / 2 - 10) # 10 is the tip length
    
    # Align right bracket
    right_bracket.mirror(p1=(0,0), p2=(0,1))
    right_bracket.movex(bar_length / 2 + 10)
    
    return c

if __name__ == "__main__":
    c = create_device()
    c.write_gds("device_optimized.gds")
    # c.show() # Uncomment to view in KLayout