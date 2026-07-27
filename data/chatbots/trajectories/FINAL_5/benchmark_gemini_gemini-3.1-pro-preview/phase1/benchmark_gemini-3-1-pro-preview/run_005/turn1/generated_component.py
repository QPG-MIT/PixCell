import gdsfactory as gf

@gf.cell
def asymmetric_grating_coupler():
    c = gf.Component("asymmetric_grating_coupler")
    
    # Parametric constraints meticulously tuned for exact 18.24 x 0.7 um footprint
    w = 0.04
    grating_pitch = 0.10
    w_t = grating_pitch * 0.5  # 50% duty cycle tooth width
    num_bars = 160
    track_pitch = 0.10         # Vertical pitch between tracks
    
    # Calculate exact straight section length
    L_straight = (2 * num_bars - 1) * w_t  # 15.95 um
    x_start = -L_straight / 2
    x_end = L_straight / 2
    
    # Tuned sweep parameters to precisely reach total width (18.24) and height (0.7)
    L_taper = 1.0158
    sweep_R = 1.0
    sweep_angle = -8  # Degrees
    
    xs = gf.cross_section.cross_section(width=w)
    
    # Define track vertical Y-centers
    y_center = 0.0
    y_top_g = track_pitch
    y_top_s = track_pitch * 2
    y_bot_g = -track_pitch
    y_bot_s = -track_pitch * 2
    
    # ==========================================
    # 1. Central Line (Track 3)
    # ==========================================
    rect_c = c << gf.components.rectangle(size=(L_straight, w), centered=True)
    rect_c.move((0, y_center))
    
    taper_c_r = c << gf.components.taper(length=L_taper, width1=w, width2=0.005)
    taper_c_r.move((x_end, y_center))
    
    taper_c_l = c << gf.components.taper(length=L_taper, width1=w, width2=0.005)
    taper_c_l.rotate(180)
    taper_c_l.move((x_start, y_center))
    
    # ==========================================
    # 2. Gratings (Tracks 2 & 4)
    # ==========================================
    rect_g = gf.components.rectangle(size=(w_t, w), centered=True)
    for i in range(num_bars):
        # Precise placement loop replacing the array method
        rx = x_start + w_t/2 + i * grating_pitch
        
        ref_t = c << rect_g
        ref_t.move((rx, y_top_g))
        
        ref_b = c << rect_g
        ref_b.move((rx, y_bot_g))
        
    taper_tg_l = c << gf.components.taper(length=L_taper, width1=w, width2=0.005)
    taper_tg_l.rotate(180)
    taper_tg_l.move((x_start, y_top_g))
    
    taper_bg_r = c << gf.components.taper(length=L_taper, width1=w, width2=0.005)
    taper_bg_r.move((x_end, y_bot_g))
    
    # ==========================================
    # 3. Top Solid (Track 1)
    # ==========================================
    rect_ts = c << gf.components.rectangle(size=(L_straight, w), centered=True)
    rect_ts.move((0, y_top_s))
    
    # U-Bend Top Right
    u_top = c << gf.components.bend_circular(radius=track_pitch/2, angle=-180, cross_section=xs)
    u_top.move((x_end, y_top_s))
    
    # Sweep & Taper Top Left
    sw_top_bend = c << gf.components.bend_circular(radius=sweep_R, angle=sweep_angle, cross_section=xs)
    sw_top_bend.rotate(180)
    sw_top_bend.move((x_start, y_top_s))
    
    sw_top_taper = c << gf.components.taper(length=L_taper, width1=w, width2=0.005)
    sw_top_taper.connect("o1", sw_top_bend.ports["o2"])
    
    # ==========================================
    # 4. Bottom Solid (Track 5)
    # ==========================================
    rect_bs = c << gf.components.rectangle(size=(L_straight, w), centered=True)
    rect_bs.move((0, y_bot_s))
    
    # U-Bend Bottom Left
    u_bot = c << gf.components.bend_circular(radius=track_pitch/2, angle=-180, cross_section=xs)
    u_bot.rotate(180)
    u_bot.move((x_start, y_bot_s))
    
    # Sweep & Taper Bottom Right
    sw_bot_bend = c << gf.components.bend_circular(radius=sweep_R, angle=sweep_angle, cross_section=xs)
    sw_bot_bend.move((x_end, y_bot_s))
    
    sw_bot_taper = c << gf.components.taper(length=L_taper, width1=w, width2=0.005)
    sw_bot_taper.connect("o1", sw_bot_bend.ports["o2"])
    
    return c

if __name__ == "__main__":
    device = asymmetric_grating_coupler()
    device.show()