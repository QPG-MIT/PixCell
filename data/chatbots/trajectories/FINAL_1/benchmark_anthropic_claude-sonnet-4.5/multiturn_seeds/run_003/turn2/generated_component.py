import gdsfactory as gf

@gf.cell
def tapered_waveguides():
    c = gf.Component()
    
    # Layer
    layer = (1, 0)
    
    # Waveguide parameters
    thin_width = 0.18
    medium_width = 0.55
    thick_width = 0.85
    
    # Total length
    total_length = 40.0
    
    # Top waveguide - thin, then expands upward on right
    top_y = 0.65
    top_thin_len = 24.0
    top_taper_len = 16.0
    
    top_path = gf.Path()
    top_path.append(gf.path.straight(length=top_thin_len))
    top_wg = top_path.extrude(cross_section=gf.cross_section.cross_section(width=thin_width, layer=layer))
    top_ref = c << top_wg
    top_ref.movey(top_y)
    
    # Top taper - expands more dramatically
    top_taper_path = gf.Path()
    top_taper_path.append(gf.path.straight(length=top_taper_len))
    xs_thin = gf.cross_section.cross_section(width=thin_width, layer=layer)
    xs_thick = gf.cross_section.cross_section(width=thick_width, layer=layer)
    top_taper_comp = top_taper_path.extrude_transition(
        gf.path.transition(xs_thin, xs_thick, width_type='linear')
    )
    top_taper_ref = c << top_taper_comp
    top_taper_ref.move((top_thin_len, top_y))
    
    # Middle waveguide - uniform thin, shorter length
    mid_y = 0.0
    mid_len = 29.0
    
    mid_path = gf.Path()
    mid_path.append(gf.path.straight(length=mid_len))
    mid_wg = mid_path.extrude(cross_section=gf.cross_section.cross_section(width=thin_width, layer=layer))
    mid_ref = c << mid_wg
    mid_ref.movey(mid_y)
    
    # Bottom waveguide - thin then expands dramatically downward on right
    bot_y = -0.65
    bot_thin_len = 16.0
    bot_taper_len = 24.0
    
    # Bottom thin section
    bot_path = gf.Path()
    bot_path.append(gf.path.straight(length=bot_thin_len))
    bot_wg = bot_path.extrude(cross_section=gf.cross_section.cross_section(width=thin_width, layer=layer))
    bot_ref = c << bot_wg
    bot_ref.movey(bot_y)
    
    # Bottom taper - expands dramatically
    bot_taper_path = gf.Path()
    bot_taper_path.append(gf.path.straight(length=bot_taper_len))
    bot_taper_comp = bot_taper_path.extrude_transition(
        gf.path.transition(xs_thin, xs_thick, width_type='linear')
    )
    bot_taper_ref = c << bot_taper_comp
    bot_taper_ref.move((bot_thin_len, bot_y))
    
    return c

if __name__ == "__main__":
    device = tapered_waveguides()
    device.show()
    device.write_gds("tapered_waveguides.gds")