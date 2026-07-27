import gdsfactory as gf

@gf.cell
def comb_structure() -> gf.Component:
    """
    Creates the comb-like structure shown in the image.
    Builds the shape strictly from parametric primitives and boolean operations.
    """
    c = gf.Component("CombStructure")
    
    # Define a strict cross-section to force layer (1,0) for waveguides/tapers
    xs = gf.cross_section.cross_section(layer=(1, 0))

    # 1. Main Body
    # The [25, 10] footprint matches the central rectangular body
    current_geom = gf.components.rectangle(size=(25.0, 10.0), layer=(1, 0), centered=True)

    # 2. Define the Top Peg Geometry
    @gf.cell
    def top_peg() -> gf.Component:
        # Taper section: wide base narrowing upwards
        t_comp = gf.components.taper(length=7.0, width1=2.5, width2=1.2, cross_section=xs)
        
        # Straight section: using rectangle instead of 0-slope taper for boolean reliability
        # Size is (length=5.2, width=1.2). We make it 5.2 instead of 5.0 to intentionally 
        # overlap with the taper by 0.2um and avoid exact touching edges.
        s_comp = gf.components.rectangle(size=(5.2, 1.2), layer=(1, 0), centered=True)
        
        # Position the straight section
        temp_s = gf.Component("temp_straight")
        ref = temp_s << s_comp
        # Center of rectangle at x=9.5 -> Left edge is at 9.5 - 2.6 = 6.9. 
        # Since the taper ends at x=7.0, this creates a 0.1um reliable overlap.
        ref.move((9.5, 0)) 
        
        # Union them internally so the peg acts as a single contiguous polygon
        return gf.boolean(A=t_comp, B=temp_s, operation="or", layer=(1, 0))

    peg_comp = top_peg()

    # 3. Add 4 Top Pegs sequentially
    # Centers at -9, -3, 3, 9 align perfectly across the 25um body width
    for i, x in enumerate([-9.0, -3.0, 3.0, 9.0]):
        temp_c = gf.Component(f"temp_top_pos_{i}")
        ref = temp_c << peg_comp
        # Rotate 90 degrees to point upwards
        ref.rotate(90)
        # Main body top edge is at y=5.0. Moving to y=4.5 embeds the peg 0.5um 
        # into the body, guaranteeing a smooth, gap-free boolean union.
        ref.move((x, 4.5))
        
        # Sequentially union each peg into the main structure
        current_geom = gf.boolean(A=current_geom, B=temp_c, operation="or", layer=(1, 0))

    # 4. Add the Bottom Peg
    @gf.cell
    def bottom_peg() -> gf.Component:
        # Taper pointing down
        return gf.components.taper(length=4.0, width1=2.5, width2=1.0, cross_section=xs)
        
    bot_comp = bottom_peg()
    temp_bot = gf.Component("temp_bot_pos")
    ref_bot = temp_bot << bot_comp
    # Rotate -90 degrees to point downwards
    ref_bot.rotate(-90)
    # Main body bottom edge is at y=-5.0. Moving to y=-4.5 embeds it 0.5um upwards.
    ref_bot.move((0, -4.5))
    
    # Final sequential boolean union
    current_geom = gf.boolean(A=current_geom, B=temp_bot, operation="or", layer=(1, 0))

    # Add the perfectly fused single solid geometry into our final component
    c << current_geom

    return c

if __name__ == "__main__":
    # Generate the layout
    device = comb_structure()
    
    # Save the output to a GDS file
    device.write_gds("comb_structure.gds")