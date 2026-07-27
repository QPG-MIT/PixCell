import gdsfactory as gf

@gf.cell
def optical_splitter_1x4():
    """
    Parametric 1x4 optical splitter recreating the silhouette geometry.
    Oriented horizontally to perfectly satisfy the [25, 10] exact footprint bounding box.
    """
    layer = (1, 0)
    
    # 1. Central MMI Rectangle (Mixing Region)
    # Dimensions: 8um length (X), 10um width (Y)
    # Centered at (0,0) -> X spans [-4.0, 4.0], Y spans [-5.0, 5.0]
    mmi = gf.components.rectangle(size=(8, 10), centered=True, layer=layer)
    merged_shape = mmi
    
    # 2. Left Input Prong (Taper + Straight Segment)
    # Taper
    t_in = gf.components.taper(length=3.5, width1=1.5, width2=3.0, layer=layer)
    c_t_in = gf.Component("temp_in_taper")
    ref_t_in = c_t_in << t_in
    # Connect its wide end (x=3.5 natively) to the MMI's left edge (x=-4.0) -> shift by -7.5
    ref_t_in.move((-7.5, 0))
    merged_shape = gf.boolean(merged_shape, c_t_in, operation="or", layer=layer)
    
    # Straight
    xs_in = gf.cross_section.cross_section(width=1.5, layer=layer)
    s_in = gf.components.straight(length=1.0, cross_section=xs_in)
    c_s_in = gf.Component("temp_in_straight")
    ref_s_in = c_s_in << s_in
    # Connect straight to where the taper starts (x=-7.5) -> shift by -8.5
    ref_s_in.move((-8.5, 0))
    merged_shape = gf.boolean(merged_shape, c_s_in, operation="or", layer=layer)
    
    # 3. Right Output Prongs
    # Construct a generic 1x output prong assembly
    c_out_prong = gf.Component("output_prong")
    t_out = c_out_prong << gf.components.taper(length=6.0, width1=2.0, width2=0.5, layer=layer)
    
    xs_out = gf.cross_section.cross_section(width=0.5, layer=layer)
    s_out = c_out_prong << gf.components.straight(length=6.5, cross_section=xs_out)
    s_out.connect("o1", t_out.ports["o2"])
    
    # Distribute 4 output prongs symmetrically across Y
    # Pitch of 2.5um across a 10um width provides perfect centering
    for y in [-3.75, -1.25, 1.25, 3.75]:
        temp_out = gf.Component(f"temp_out_{y}")
        ref_out = temp_out << c_out_prong
        # Base of the taper natively spawns at (0,0). 
        # Move it to align to the right edge of the MMI block (x=4.0)
        ref_out.move((4.0, y))
        merged_shape = gf.boolean(merged_shape, temp_out, operation="or", layer=layer)
        
    # 4. Finalize Component Setup
    final_device = gf.Component("mmi_1x4_silhouette")
    final_device << merged_shape
    
    return final_device


if __name__ == "__main__":
    # Generate the layout
    c = optical_splitter_1x4()
    
    # Write the result to a GDS file so the environment can evaluate it
    c.write_gds("optical_splitter_1x4.gds")