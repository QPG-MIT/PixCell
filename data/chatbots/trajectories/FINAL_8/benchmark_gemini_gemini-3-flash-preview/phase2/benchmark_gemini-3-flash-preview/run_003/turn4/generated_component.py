import gdsfactory as gf
import numpy as np

@gf.cell
def make_curved_horn(width_bottom=80.0, width_top=110.0, height=1.6, layer=(1, 0)):
    """
    Creates one half (top or bottom) of the device structure.
    Consists of a thick base bar, 4 thin bars, and curved side rails.
    """
    c = gf.Component()
    
    # 1. Define the side rail curvature (quadratic flare)
    # We use a thin rail width to match the 'wire-frame' look of the target
    rail_width = 0.25 
    y_steps = np.linspace(0, height, 40)
    
    def get_inner_half_width(y):
        # Quadratic interpolation between bottom and top width
        return (width_bottom / 2.0) + ((width_top - width_bottom) / 2.0) * (y / height)**2

    # Create paths for left and right side rails
    pts_r = [(get_inner_half_width(y) + rail_width/2.0, y) for y in y_steps]
    pts_l = [(-(get_inner_half_width(y) + rail_width/2.0), y) for y in y_steps]
    
    path_r = gf.Path(pts_r)
    path_l = gf.Path(pts_l)
    
    c << gf.path.extrude(path_r, width=rail_width, layer=layer)
    c << gf.path.extrude(path_l, width=rail_width, layer=layer)
    
    # 2. Add Horizontal Bars
    # Proportions: 1 thick base bar, then 4 thin bars
    thick_bar_h = 0.55
    thin_bar_h = 0.08
    gap_h = 0.12
    
    current_y = 0.0
    
    # First (thick) bar
    y_mid_thick = current_y + thick_bar_h/2.0
    w_thick = 2 * get_inner_half_width(y_mid_thick)
    bar_thick = c << gf.components.rectangle(size=(w_thick, thick_bar_h), layer=layer, centered=True)
    bar_thick.movey(y_mid_thick)
    
    current_y += thick_bar_h
    
    # Four subsequent thin bars
    for _ in range(4):
        current_y += gap_h
        y_mid = current_y + thin_bar_h/2.0
        # Calculate width so it fits exactly between the rails
        w_thin = 2 * get_inner_half_width(y_mid)
        bar = c << gf.components.rectangle(size=(w_thin, thin_bar_h), layer=layer, centered=True)
        bar.movey(y_mid)
        current_y += thin_bar_h
        
    return c

@gf.cell
def recreate_device_v4():
    """
    Assembles the final device within the 120um x 4um footprint.
    """
    c = gf.Component("target_device_match")
    LAYER = (1, 0)
    W_MAX = 120.0 # Length of central bars
    
    # --- 1. Central Section: 5 Thin Horizontal Bars ---
    # These are very wide compared to the horns
    c_bar_h = 0.07
    c_gap_h = 0.11
    for i in range(5):
        y_pos = (i - 2) * (c_bar_h + c_gap_h)
        bar = c << gf.components.rectangle(size=(W_MAX, c_bar_h), layer=LAYER, centered=True)
        bar.movey(y_pos)
        
    # --- 2. Horn Sections (Top and Bottom) ---
    # Centered vertically around the middle bars.
    # Total device height limit is 4um, so horns span roughly from 0.5 to 2.0 and -0.5 to -2.0
    HORN_HEIGHT = 1.55
    Y_OFFSET = 0.45 
    
    # Narrower bottom to emphasize the flare relative to the 120um central bars
    horn_comp = make_curved_horn(width_bottom=78.0, width_top=102.0, height=HORN_HEIGHT, layer=LAYER)
    
    # Add Top Horn
    t_ref = c << horn_comp
    t_ref.movey(Y_OFFSET)
    
    # Add Bottom Horn (Mirrored)
    b_ref = c << horn_comp
    b_ref.mirror_y()
    b_ref.movey(-Y_OFFSET)
    
    return c

if __name__ == "__main__":
    device = recreate_device_v4()
    
    # Output footprint verification
    print(f"Device Dimensions: {device.xsize:.2f}um x {device.ysize:.2f}um")
    
    device.write_gds("improved_device.gds")
    device.show()