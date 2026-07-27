import gdsfactory as gf

@gf.cell
def directional_coupler_refined():
    c = gf.Component()
    
    # 1. Dimensions based on Footprint (18x3)
    length = 18.0
    height = 3.0
    
    # Waveguide parameters
    wg_width = 0.5
    gap = 0.2  # Minimum gap in the coupling region
    
    # Interaction region length
    # Adding a straight section creates a "racetrack" coupler profile
    # which is more realistic than two back-to-back S-bends.
    lc = 2.0 
    
    # Calculate S-bend length
    # The remaining length is split between the input and output bends
    lb = (length - lc) / 2
    
    # Calculate vertical positions
    # Outer boundaries are y = +1.5 and y = -1.5
    # Port centers (start/end y):
    y_top_port = (height/2) - (wg_width/2)  # 1.5 - 0.25 = 1.25
    y_bot_port = -y_top_port                # -1.25
    
    # Coupling region centers (middle y):
    # Gap is centered at y=0.
    y_top_c = (gap/2) + (wg_width/2)        # 0.1 + 0.25 = 0.35
    y_bot_c = -y_top_c                      # -0.35
    
    # Vertical displacement for S-bends
    dy = y_top_port - y_top_c               # 1.25 - 0.35 = 0.9
    
    xs = gf.cross_section.cross_section(width=wg_width)

    # 2. Build Top Arm
    # Top-Left S-bend (converging)
    # size=(x, y). Moves horizontal by lb, vertical by -dy.
    tl = c << gf.components.bend_s(size=(lb, -dy), cross_section=xs)
    tl.move((0, y_top_port))
    
    # Top Middle Straight (Coupling Region)
    tm = c << gf.components.straight(length=lc, cross_section=xs)
    tm.connect("o1", tl.ports["o2"])
    
    # Top-Right S-bend (diverging)
    # Moves horizontal by lb, vertical by +dy.
    tr = c << gf.components.bend_s(size=(lb, dy), cross_section=xs)
    tr.connect("o1", tm.ports["o2"])
    
    # 3. Build Bottom Arm
    # Bottom-Left S-bend (converging)
    # Moves horizontal by lb, vertical by +dy (upwards).
    bl = c << gf.components.bend_s(size=(lb, dy), cross_section=xs)
    bl.move((0, y_bot_port))
    
    # Bottom Middle Straight (Coupling Region)
    bm = c << gf.components.straight(length=lc, cross_section=xs)
    bm.connect("o1", bl.ports["o2"])
    
    # Bottom-Right S-bend (diverging)
    # Moves horizontal by lb, vertical by -dy (downwards).
    br = c << gf.components.bend_s(size=(lb, -dy), cross_section=xs)
    br.connect("o1", bm.ports["o2"])
    
    # 4. Expose Ports
    c.add_port("o1", port=tl.ports["o1"])
    c.add_port("o2", port=bl.ports["o1"])
    c.add_port("o3", port=tr.ports["o2"])
    c.add_port("o4", port=br.ports["o2"])
    
    return c

# Generate and save
device = directional_coupler_refined()
device.write_gds("directional_coupler_refined.gds")