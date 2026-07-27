import gdsfactory as gf

@gf.cell
def photonic_racetrack_mzi_v4():
    """
    Final Refinement:
    - Corrects geometric artifacts at connection points by tuning arm width.
    - Thickens outer ring to match reference bold style.
    - Optimizes boolean windows and hub integration.
    """
    c = gf.Component()
    
    # --- Dimensions & Parameters ---
    width_total = 5.5
    height_total = 3.0
    layer_main = (1, 0)
    
    # Feature Dimensions
    width_ring = 0.85       # Bold outer ring
    height_pad = 0.5        # Height of central rectangular pads
    
    # Arm Width Optimization:
    # To avoid the arm corners sticking out above the pad (creating a "step"),
    # Width must be <= Pad_Height * cos(Angle).
    # Angle is approx 20 degrees -> cos(20) ~ 0.94.
    # 0.5 * 0.94 = 0.47. We use 0.46 for a safe, smooth fit.
    width_arm = 0.46        
    
    pad_y_center = 0.42     # Vertical position of phase shifters
    hub_x_pos = 1.6         # Horizontal position of end couplers
    hub_size = 0.75         # Size of end coupler blocks
    
    # Cross Sections
    xs_ring = gf.cross_section.cross_section(width=width_ring, layer=layer_main)
    xs_arm = gf.cross_section.cross_section(width=width_arm, layer=layer_main)

    # --- 1. Construct Outer Racetrack ---
    # Radius derived to keep total height exactly 3.0um
    r_center = (height_total - width_ring) / 2
    l_straight = width_total - height_total # 2.5
    
    p_ring = gf.Path()
    p_ring.append(gf.path.straight(length=l_straight))
    p_ring.append(gf.path.arc(radius=r_center, angle=-180))
    p_ring.append(gf.path.straight(length=l_straight))
    p_ring.append(gf.path.arc(radius=r_center, angle=-180))
    
    ring = c << gf.path.extrude(p_ring, cross_section=xs_ring)
    ring.move(origin=ring.center, destination=(0,0))

    # --- 2. Construct Central Pads with Windows ---
    def create_pad_structure():
        # Solid Body
        c_body = gf.components.rectangle(size=(1.6, height_pad), layer=layer_main, centered=True)
        
        # Windows Component
        c_windows = gf.Component()
        w_width = 0.6
        w_height = 0.26
        gap = 0.12 # Thin bar between windows
        
        # Left Window
        w1 = c_windows << gf.components.rectangle(size=(w_width, w_height), layer=layer_main, centered=True)
        w1.movex(-(w_width + gap)/2)
        
        # Right Window
        w2 = c_windows << gf.components.rectangle(size=(w_width, w_height), layer=layer_main, centered=True)
        w2.movex((w_width + gap)/2)
        
        # Boolean Subtract (Body - Windows)
        return gf.boolean(A=c_body, B=c_windows, operation="not", layer=layer_main)

    pad_ref = create_pad_structure()
    
    # Place Top and Bottom Pads
    pad_top = c << pad_ref
    pad_top.move((0, pad_y_center))
    
    pad_bot = c << pad_ref
    pad_bot.move((0, -pad_y_center))

    # --- 3. Construct End Hubs ---
    hub_shape = gf.components.rectangle(size=(hub_size, hub_size), layer=layer_main, centered=True)
    
    hub_r = c << hub_shape
    hub_r.move((hub_x_pos, 0))
    
    hub_l = c << hub_shape
    hub_l.move((-hub_x_pos, 0))

    # --- 4. Construct Connecting Arms ---
    # Coordinates chosen to start inside the Pad and end deep inside the Hub
    # This overlap ensures a "watertight" visual with no notches.
    
    x_start = 0.65   # Inside Pad (edge is at 0.8)
    x_end = 1.45     # Inside Hub (edge starts at ~1.22)
    
    y_target = 0.08  # Converge near y=0 to form the sharp "V" shape
    
    # Define paths
    points_tr = [(x_start, pad_y_center), (x_end, y_target)]
    points_br = [(x_start, -pad_y_center), (x_end, -y_target)]
    points_tl = [(-x_start, pad_y_center), (-x_end, y_target)]
    points_bl = [(-x_start, -pad_y_center), (-x_end, -y_target)]
    
    # Extrude
    c << gf.path.extrude(gf.Path(points_tr), cross_section=xs_arm)
    c << gf.path.extrude(gf.Path(points_br), cross_section=xs_arm)
    c << gf.path.extrude(gf.Path(points_tl), cross_section=xs_arm)
    c << gf.path.extrude(gf.Path(points_bl), cross_section=xs_arm)

    return c

if __name__ == "__main__":
    device = photonic_racetrack_mzi_v4()
    device.show() 
    device.write_gds("photonic_device_v4.gds")
    
    print(f"Device Footprint: {device.dxsize:.2f} x {device.dysize:.2f} um")