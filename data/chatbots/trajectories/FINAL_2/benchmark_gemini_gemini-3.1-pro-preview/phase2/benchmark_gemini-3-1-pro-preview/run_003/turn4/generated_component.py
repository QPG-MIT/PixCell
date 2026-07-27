import gdsfactory as gf

@gf.cell
def optical_splitter_1x4_vertical():
    """
    Parametric 1x4 optical splitter recreating the silhouette geometry.
    Oriented vertically to perfectly satisfy the [25, 10] footprint bounding box.
    
    Refinements from previous iteration:
    - Central rectangle height reduced slightly for better proportion.
    - Top prongs are made significantly longer, with a 50/50 split between taper and straight sections.
    - Top prong bases widened (width1=4.6) and pitch adjusted (6.0) to accurately match the narrow gap ratio.
    - Bottom prong made shorter and stouter to better match the target silhouette.
    """
    layer = (1, 0)
    
    # Component to hold all prong parts before boolean union
    prongs = gf.Component("all_prongs")
    
    # 1. Central Rectangle
    # To satisfy the 25x10 bounding box perfectly, we span X from -12.5 to 12.5.
    # We assign Y range from -4.0 to 0.2 (Height 4.2). Centered at Y = -1.9.
    rect_comp = gf.Component("rect_temp")
    rect_ref = rect_comp << gf.components.rectangle(size=(25.0, 4.2), centered=True, layer=layer)
    rect_ref.move((0, -1.9))
    
    # 2. Bottom Input Prong
    # Spans exactly from Y = -5.0 to Y = -4.0 (Length 1.0)
    # Width tapers from 1.2 (tip) to 2.4 (base at rectangle)
    t_bot = gf.components.taper(length=1.0, width1=1.2, width2=2.4, layer=layer)
    ref_bot = prongs << t_bot
    ref_bot.rotate(90)
    # Move so the narrow tip is at Y=-5.0 and the wide base meets the rectangle at Y=-4.0 
    ref_bot.move((0, -5.0))
    
    # 3. Top Output Prongs
    # Total length 4.8, spanning Y: [0.2, 5.0]
    # Taper section spans Y: [0.2, 2.6] (Length 2.4)
    # Straight section spans Y: [2.6, 5.0] (Length 2.4)
    t_top = gf.components.taper(length=2.4, width1=4.6, width2=1.0, layer=layer)
    xs_top = gf.cross_section.cross_section(width=1.0, layer=layer)
    s_top = gf.components.straight(length=2.4, cross_section=xs_top)
    
    # Distribute the 4 prongs across the 25um width cleanly
    # Centers at -9.0, -3.0, 3.0, 9.0 gives a uniform Pitch = 6.0um
    for x in [-9.0, -3.0, 3.0, 9.0]:
        # Taper Section
        ref_t = prongs << t_top
        ref_t.rotate(90)
        # Move so wide base connects perfectly flush with rectangle top at Y=0.2
        ref_t.move((x, 0.2))
        
        # Straight Extension Section
        ref_s = prongs << s_top
        ref_s.rotate(90)
        # Move so it connects perfectly where the top taper ends at Y=2.6
        ref_s.move((x, 2.6))
        
    # 4. Assembly & Boolean Composition
    # Fuse the central rectangle and all the perfectly touching prongs into a single, seamless monolithic polygon
    merged_shape = gf.boolean(rect_comp, prongs, operation="or", layer=layer)
    
    # Finalize the Component
    final_device = gf.Component("mmi_1x4_vertical_matched")
    final_device << merged_shape
    
    return final_device

if __name__ == "__main__":
    # Generate the layout
    c = optical_splitter_1x4_vertical()
    
    # Write the result to a GDS file for evaluation
    c.write_gds("optical_splitter_1x4_vertical.gds")