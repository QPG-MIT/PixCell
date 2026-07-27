import gdsfactory as gf

@gf.cell
def tapered_bar_array(
    n_lines: int = 5,
    line_width: float = 4.0, # Height of each bar
    spacing: float = 3.0,    # Gap between bars
    min_length: float = 40.0,
    max_length: float = 120.0
):
    """
    Creates a stack of rectangular bars with a tapered barrel-like length profile.
    """
    c = gf.Component("tapered_bar_array")
    
    # Calculate step size to grow from min_length to max_length
    # Center index is 2 for n=5
    center_idx = (n_lines - 1) // 2
    step = (max_length - min_length) / center_idx
    
    # Cross section for the bars (layer 1,0)
    xs = gf.cross_section.cross_section(width=line_width, layer=(1, 0))
    
    for i in range(n_lines):
        # Calculate length based on distance from center
        # Center is longest, edges are shortest
        dist_from_center = abs(i - center_idx)
        length = max_length - (dist_from_center * step)
        
        # Create the straight bar
        bar = c << gf.components.straight(length=length, cross_section=xs)
        
        # Calculate vertical position
        y_pos = (i - center_idx) * (line_width + spacing)
        
        # Move bar to position (centered horizontally at x=0)
        bar.movex(-length / 2)
        bar.movey(y_pos)
        
    return c

# 1. Generate the component
device = tapered_bar_array()

# 2. Write the GDS file
file_path = "tapered_bar_array.gds"
device.write_gds(file_path)

print(f"Success! GDS file produced at: {file_path}")