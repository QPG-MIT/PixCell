import gdsfactory as gf

@gf.cell
def photonic_racetrack_mzi_v2():
    """
    Refined recreation of the device:
    - Racetrack ring (3.0um x 5.5um footprint)
    - Hollow rectangular frames for phase shifters
    - Thick diagonal waveguides connecting to end couplers
    """
    c = gf.Component()
    
    # --- Dimensions & Parameters ---
    # Global Constraints
    width_total = 5.5
    height_total = 3.0
    layer_main = (1, 0)
    
    # Component Dimensions (Estimated from image)
    ring_width = 0.55        # Thickness of outer ring
    inner_wg_width = 0.35    # Thickness of diagonal arms (significantly thicker than before)
    
    pad_size = (1.1, 0.55)   # Outer size of central pads
    pad_hole_size = (0.6, 0.25) # Size of the cut-out inside pads
    pad_spacing = 0.95       # Center-to-center vertical spacing
    
    hub_size = (0.65, 0.75)  # Size of end coupler blocks
    
    # Cross Sections
    xs_ring = gf.cross_section.cross_section(width=ring_width, layer=layer_main)
    xs_inner = gf.cross_section.cross_section(width=inner_wg_width, layer=layer_main)

    # --- 1. Construct Outer Racetrack ---
    # To fit exactly in height 3.0 with line width 0.55:
    # Outer Radius = 1.5. 
    # Centerline Radius = 1.5 - (0.55 / 2) = 1.225
    r_center = (height_total / 2) - (ring_width / 2)
    l_straight = width_total - height_total # 2.5um straight sections
    
    # Define Path: Top Straight -> Right Arc -> Bottom Straight -> Left Arc
    p = gf.Path()
    p.append(gf.path.straight(length=l_straight))
    p.append(gf.path.arc(radius=r_center, angle=-180))
    p.append(gf.path.straight(length=l_straight))
    p.append(gf.path.arc(radius=r_center, angle=-180))
    
    # Extrude and Center
    ring = c << gf.path.extrude(p, cross_section=xs_ring)
    ring.move(origin=ring.center, destination=(0,0))

    # --- 2. Construct Hollow Central Pads ---
    # Define a sub-component for the hollow pad to reuse it
    def create_hollow_pad():
        temp_c = gf.Component()
        outer = temp_c << gf.components.rectangle(size=pad_size, layer=layer_main, centered=True)
        inner = temp_c << gf.components.rectangle(size=pad_hole_size, layer=layer_main, centered=True)
        
        # Boolean subtract: Outer NOT Inner
        # Note: gf.boolean returns a new Component
        return gf.boolean(A=outer, B=inner, operation="not", layer=layer_main)

    hollow_pad_ref = create_hollow_pad()
    
    # Place Top Pad
    pad_top = c << hollow_pad_ref
    pad_top.move((0, pad_spacing/2))
    
    # Place Bottom Pad
    pad_bot = c << hollow_pad_ref
    pad_bot.move((0, -pad_spacing/2))

    # --- 3. Construct End Hubs ---
    # Calculate X position: Center of straight section is x=0. 
    # End of straight is +/- l_straight/2 = +/- 1.25.
    # We want hubs slightly inside the curve start.
    x_hub_center = (l_straight / 2) + 0.1 
    
    hub_right = c << gf.components.rectangle(size=hub_size, layer=layer_main, centered=True)
    hub_right.move((x_hub_center, 0))
    
    hub_left = c << gf.components.rectangle(size=hub_size, layer=layer_main, centered=True)
    hub_left.move((-x_hub_center, 0))

    # --- 4. Construct Connecting Arms ---
    # Connect the outer edge of the pads to the inner edge of the hubs
    
    # Coordinates
    x_pad_edge = pad_size[0] / 2
    y_pad_top = pad_spacing / 2
    y_pad_bot = -pad_spacing / 2
    
    # We target the corners of the hub for a "V" shape merge
    x_hub_inner = x_hub_center - (hub_size[0] / 2) + 0.1 # Overlap slightly
    y_hub_top_target = 0.15 
    y_hub_bot_target = -0.15
    
    # Top Right Arm
    ptr = gf.Path([(x_pad_edge, y_pad_top), (x_hub_inner, y_hub_top_target)])
    c << gf.path.extrude(ptr, cross_section=xs_inner)

    # Bottom Right Arm
    pbr = gf.Path([(x_pad_edge, y_pad_bot), (x_hub_inner, y_hub_bot_target)])
    c << gf.path.extrude(pbr, cross_section=xs_inner)
    
    # Top Left Arm
    ptl = gf.Path([(-x_pad_edge, y_pad_top), (-x_hub_inner, y_hub_top_target)])
    c << gf.path.extrude(ptl, cross_section=xs_inner)

    # Bottom Left Arm
    pbl = gf.Path([(-x_pad_edge, y_pad_bot), (-x_hub_inner, y_hub_bot_target)])
    c << gf.path.extrude(pbl, cross_section=xs_inner)

    return c

if __name__ == "__main__":
    device = photonic_racetrack_mzi_v2()
    device.show() 
    device.write_gds("photonic_device_v2.gds")
    
    # Using dxsize/dysize for dimensions in microns
    print(f"Device Footprint: {device.dxsize:.2f} x {device.dysize:.2f} um")