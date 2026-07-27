import gdsfactory as gf

@gf.cell
def recreate_curved_device():
    """
    Recreates the symmetric curved waveguide device from the provided image.
    Footprint constraint: 18um (length) x 3um (height).
    """
    # 1. Define device dimensions based on footprint [18, 3]
    total_length = 18.0
    total_height = 3.0
    
    # Estimated visual parameters to match the image:
    wg_width = 0.7      # Waveguide thickness
    center_gap = 0.3    # Minimum gap at the center
    
    # Each arm consists of two S-bends joined in the middle.
    dx = total_length / 2
    
    # Calculate vertical centers to satisfy the 3um height boundary:
    # Outer edge must be at +/- 1.5um. So center is at +/- (1.5 - wg_width/2)
    y_outer_center = (total_height / 2) - (wg_width / 2) 
    
    # Center of waveguide at the mid-point (gap):
    y_inner_center = (center_gap / 2) + (wg_width / 2)
    
    # The vertical offset (dy) required for each S-bend segment:
    dy = y_outer_center - y_inner_center
    
    c = gf.Component("recreated_curved_device")
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))
    
    # 2. Build the Top Arm
    # Left segment: curves DOWN from the edge to the center
    top_l = c << gf.components.bend_s(size=(dx, -dy), cross_section=xs)
    top_l.movey(y_outer_center)
    
    # Right segment: curves back UP from the center to the edge
    top_r = c << gf.components.bend_s(size=(dx, dy), cross_section=xs)
    top_r.connect("o1", top_l.ports["o2"])
    
    # 3. Build the Bottom Arm (Mirror symmetry)
    # Left segment: curves UP from the edge to the center
    bot_l = c << gf.components.bend_s(size=(dx, dy), cross_section=xs)
    bot_l.movey(-y_outer_center)
    
    # Right segment: curves back DOWN from the center to the edge
    bot_r = c << gf.components.bend_s(size=(dx, -dy), cross_section=xs)
    bot_r.connect("o1", bot_l.ports["o2"])
    
    # Center the component for standard layout practice
    c.movex(-total_length / 2)
    
    return c

if __name__ == "__main__":
    # Create the component
    device = recreate_curved_device()
    
    # Save the geometry to a GDS file
    output_filename = "curved_device_output.gds"
    device.write_gds(output_filename)
    
    print(f"Successfully produced: {output_filename}")