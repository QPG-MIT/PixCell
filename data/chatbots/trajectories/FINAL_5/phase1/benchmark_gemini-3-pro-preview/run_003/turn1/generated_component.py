import gdsfactory as gf
import numpy as np

# 1. Define the basic Cross Section
# The catalog emphasizes using cross_sections for layer control.
xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))

@gf.cell
def straight_grating(
    length=100.0, 
    width=0.5, 
    period=0.6, 
    duty_cycle=0.5, 
    tooth_depth=0.2, 
    teeth_direction=-1 # -1 for down (bottom), 1 for up (top)
):
    c = gf.Component()
    
    # FIX: Create a cross-section to pass width and layer to straight()
    xs_grating = gf.cross_section.cross_section(width=width, layer=(1,0))
    
    # Base straight waveguide using cross_section
    wg = c << gf.components.straight(length=length, cross_section=xs_grating)
    c.add_ports(wg.ports)
    
    # Calculate teeth parameters
    tooth_width = period * duty_cycle
    num_teeth = int(length // period)
    
    # Create the tooth shape
    # gf.components.rectangle explicitly allows 'layer' per the catalog
    tooth_shape = gf.components.rectangle(
        size=(tooth_width, tooth_depth), 
        layer=(1,0), 
        centered=True
    )
    
    # Add teeth in a loop
    for i in range(num_teeth):
        t = c << tooth_shape
        x_pos = (i * period) + (period / 2)
        # Calculate y position: edge of waveguide + half tooth height
        y_offset = (width/2 + tooth_depth/2) * teeth_direction
        t.move((x_pos, y_offset))
        
    return c

@gf.cell
def contra_directional_coupler():
    c = gf.Component()
    
    # --- Parameters ---
    coupling_length = 80.0
    bend_radius = 10.0
    gap = 0.2
    wg_width = 0.5
    
    # --- Central Bus ---
    bus_length = coupling_length + 2 * bend_radius + 40
    bus = c << gf.components.straight(length=bus_length, cross_section=xs)
    bus.movex(-bus_length/2)
    
    # --- Top Loop Construction ---
    # 1. Grating Arm (Teeth pointing DOWN towards bus)
    top_grating = c << straight_grating(
        length=coupling_length, 
        width=wg_width,
        teeth_direction=-1
    )
    # Position: shift up by (width + gap + width)/2 relative to bus center
    y_top = (wg_width + gap + wg_width)/2
    top_grating.movey(y_top)
    top_grating.movex(-coupling_length/2) # Center horizontally

    # 2. Right Bend (180 degrees)
    bend_top = c << gf.components.bend_euler(
        radius=bend_radius, 
        angle=180, 
        cross_section=xs
    )
    bend_top.connect("o1", top_grating.ports["o2"])
    
    # 3. Top Return Arm (Plain Straight)
    top_return = c << gf.components.straight(length=coupling_length, cross_section=xs)
    top_return.connect("o1", bend_top.ports["o2"])
    
    # 4. Input Curve (S-Bend/Arc away)
    input_curve_top = c << gf.components.bend_euler(
        radius=bend_radius, 
        angle=45, 
        cross_section=xs
    )
    input_curve_top.connect("o1", top_return.ports["o2"])
    
    # 5. Termination Taper for the Grating Arm (Left side)
    # FIX: Use cross_section instead of layer
    taper_top = c << gf.components.taper(
        length=10, 
        width1=wg_width, 
        width2=0.05, 
        cross_section=xs
    )
    taper_top.connect("o1", top_grating.ports["o1"])

    # --- Bottom Loop Construction (Mirrored logic) ---
    # 1. Grating Arm (Teeth pointing UP towards bus)
    bot_grating = c << straight_grating(
        length=coupling_length, 
        width=wg_width,
        teeth_direction=1
    )
    y_bot = -(wg_width + gap + wg_width)/2
    bot_grating.movey(y_bot)
    bot_grating.movex(-coupling_length/2)

    # 2. Left Bend (180 degrees)
    bend_bot = c << gf.components.bend_euler(
        radius=bend_radius, 
        angle=180, 
        cross_section=xs
    )
    # Connect to the LEFT port of the grating (o1)
    bend_bot.connect("o2", bot_grating.ports["o1"])
    
    # 3. Bottom Return Arm
    bot_return = c << gf.components.straight(length=coupling_length, cross_section=xs)
    bot_return.connect("o2", bend_bot.ports["o1"])
    
    # 4. Output Curve (S-Bend/Arc away)
    output_curve_bot = c << gf.components.bend_euler(
        radius=bend_radius, 
        angle=45, 
        cross_section=xs
    )
    # Mirror the bend to curve downwards
    output_curve_bot.mirror() 
    output_curve_bot.connect("o1", bot_return.ports["o1"])
    
    # 5. Termination Taper for the Grating Arm (Right side)
    # FIX: Use cross_section instead of layer
    taper_bot = c << gf.components.taper(
        length=10, 
        width1=wg_width, 
        width2=0.05, 
        cross_section=xs
    )
    taper_bot.connect("o1", bot_grating.ports["o2"])

    return c

if __name__ == "__main__":
    device = contra_directional_coupler()
    device.write_gds("contra_directional_coupler.gds")
    device.show()