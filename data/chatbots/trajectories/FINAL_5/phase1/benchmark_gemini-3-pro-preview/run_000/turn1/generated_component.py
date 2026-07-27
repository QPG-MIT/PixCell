import gdsfactory as gf
import numpy as np

# 1. Define Basic Parameters
wg_width = 0.5
layer_wg = (1, 0)

# Grating Parameters
period = 0.6
duty_cycle = 0.5
num_periods = 80
grating_length = num_periods * period

# Bend Parameters
bend_radius = 5.0  # 5.0 um is safe for grid if angle is 90

# 2. Define a Custom Component for the Segmented (Grating) Arm
@gf.cell
def segmented_waveguide_arm(n_periods=80, p=0.6, dc=0.5, w=0.5):
    """
    Creates a segmented waveguide using a loop of rectangles.
    Centered at (0,0) for easier placement.
    """
    c = gf.Component()
    
    segment_length = p * dc
    
    # Define the primitive rectangle component once
    rect_comp = gf.components.rectangle(size=(segment_length, w), layer=layer_wg, centered=True)
    
    # Calculate offset to center the whole array at x=0
    x_offset = - ((n_periods - 1) * p) / 2.0
    
    # Place segments manually to avoid version-dependent array functions
    for i in range(n_periods):
        ref = c << rect_comp
        ref.movex(i * p + x_offset)
        
    # Add ports at the exact geometric edges of the array
    x_start = x_offset - segment_length / 2
    x_end = x_offset + (n_periods - 1) * p + segment_length / 2
    
    c.add_port(
        "o1", 
        center=(x_start, 0), 
        width=w, 
        orientation=180, 
        layer=layer_wg
    )
    
    c.add_port(
        "o2", 
        center=(x_end, 0), 
        width=w, 
        orientation=0, 
        layer=layer_wg
    )
    
    return c

@gf.cell
def contra_directional_coupler_device():
    c = gf.Component()
    
    # Define cross-section with explicitly defined radius to satisfy validation
    xs = gf.cross_section.cross_section(width=wg_width, layer=layer_wg, radius=bend_radius)

    # --- Instantiate the Central Gratings ---
    gap = 0.3 # Gap between the two gratings
    
    # Create the grating component
    grating_comp = segmented_waveguide_arm(n_periods=num_periods, p=period, dc=duty_cycle, w=wg_width)
    
    # Top Grating Arm
    grating_top = c << grating_comp
    grating_top.x = 0
    grating_top.y = gap/2 + wg_width/2
    
    # Bottom Grating Arm
    grating_bot = c << grating_comp
    grating_bot.x = 0
    grating_bot.y = -gap/2 - wg_width/2

    # --- Top Half Assembly ---
    # 1. Right Loop (180 bend UP)
    # Connects to the Right port (o2) of the Top Grating.
    bend_top = c << gf.components.bend_euler(radius=bend_radius, angle=180, cross_section=xs)
    bend_top.connect("o1", grating_top.ports["o2"])
    
    # 2. Return Waveguide (Solid, runs right to left)
    return_len = grating_length + 2 * bend_radius + 10
    wg_top_return = c << gf.components.straight(length=return_len, cross_section=xs)
    wg_top_return.connect("o1", bend_top.ports["o2"])
    
    # 3. Output Taper (Left end of return WG)
    taper_top_out = c << gf.components.taper(length=10, width1=wg_width, width2=0.05, layer=layer_wg)
    taper_top_out.connect("o1", wg_top_return.ports["o2"])
    
    # 4. Input Curve (Left end of grating)
    # Curves UP and AWAY.
    # Connecting to o1 (Left, 180).
    # Using angle=90 to ensure grid alignment (endpoint is exactly at x+/-R, y+/-R).
    bend_input_top = c << gf.components.bend_euler(radius=bend_radius, angle=90, cross_section=xs)
    bend_input_top.mirror_y() 
    bend_input_top.connect("o1", grating_top.ports["o1"])
    
    # 5. Input Taper
    taper_top_in = c << gf.components.taper(length=5, width1=wg_width, width2=0.05, layer=layer_wg)
    taper_top_in.connect("o1", bend_input_top.ports["o2"])


    # --- Bottom Half Assembly ---
    # 1. Left Loop (180 bend DOWN)
    # Connects to Left port (o1) of Bottom Grating.
    bend_bot = c << gf.components.bend_euler(radius=bend_radius, angle=180, cross_section=xs)
    bend_bot.connect("o1", grating_bot.ports["o1"])
    
    # 2. Return Waveguide (Solid, runs left to right)
    wg_bot_return = c << gf.components.straight(length=return_len, cross_section=xs)
    wg_bot_return.connect("o1", bend_bot.ports["o2"])
    
    # 3. Output Taper (Right end of return WG)
    taper_bot_out = c << gf.components.taper(length=10, width1=wg_width, width2=0.05, layer=layer_wg)
    taper_bot_out.connect("o1", wg_bot_return.ports["o2"])
    
    # 4. Input Curve (Right end of grating)
    # Curves DOWN and AWAY.
    # Connects to Right port (o2, 0).
    # Using angle=90 for grid alignment.
    bend_input_bot = c << gf.components.bend_euler(radius=bend_radius, angle=90, cross_section=xs)
    bend_input_bot.mirror_y()
    bend_input_bot.connect("o1", grating_bot.ports["o2"])
    
    # 5. Input Taper
    taper_bot_in = c << gf.components.taper(length=5, width1=wg_width, width2=0.05, layer=layer_wg)
    taper_bot_in.connect("o1", bend_input_bot.ports["o2"])

    # --- Central Decoration / Divider Line ---
    divider_len = grating_length + 10
    divider = c << gf.components.rectangle(size=(divider_len, 0.1), layer=layer_wg, centered=True)
    divider.x = 0
    divider.y = 0

    return c

# Generate and Save
device = contra_directional_coupler_device()
device.write_gds("contra_coupler.gds")
device.show()