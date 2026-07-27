import gdsfactory as gf
import numpy as np

# 1. Define clean cross-sections
# Waveguide (layer 1,0)
xs_wg = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
# Grating stripes (layer 2,0) - Different layer ensures they remain distinct
xs_grating = gf.cross_section.cross_section(width=0.5, layer=(2, 0))

@gf.cell
def central_grating_waveguide(length=18.24):
    c = gf.Component()
    
    # Create the base waveguide
    wg = c << gf.components.straight(length=length, cross_section=xs_wg)
    
    # Create segments (gratings)
    num_stripes = 40
    stripe_width = 0.1
    spacing = length / num_stripes
    
    # Create a single stripe component to array
    stripe = gf.components.rectangle(size=(stripe_width, 0.8), layer=(2, 0), centered=True)
    
    # Add stripes along the length
    for i in range(num_stripes):
        x_pos = (i * spacing) - (length/2) + (spacing/2)
        s = c << stripe
        s.movex(x_pos)
        
    return c

@gf.cell
def u_shaped_arm():
    """Creates a U-shaped arm with tapered ends using Path."""
    c = gf.Component()
    
    # Define a path that goes: Straight -> 180 Bend -> Straight
    p = gf.Path()
    p.append(gf.path.straight(length=5))
    p.append(gf.path.euler(radius=2.0, angle=180))
    p.append(gf.path.straight(length=5))
    
    # Extrude path into a waveguide
    arm = c << gf.path.extrude(p, cross_section=xs_wg)
    
    # Add sharp tapers to the ends (the "spear tips")
    taper_in = c << gf.components.taper(length=2, width1=0.1, width2=0.5)
    taper_out = c << gf.components.taper(length=2, width1=0.5, width2=0.1)
    
    taper_in.connect("o2", arm.ports["o1"])
    taper_out.connect("o1", arm.ports["o2"])
    
    # Expose ports
    c.add_port("o1", port=taper_in.ports["o1"])
    c.add_port("o2", port=taper_out.ports["o2"])
    
    return c

@gf.cell
def full_device():
    c = gf.Component()
    
    # 1. Add center
    center = c << central_grating_waveguide()
    
    # 2. Add Top Arm
    top_arm = c << u_shaped_arm()
    # Position: shift Y up so it doesn't overlap the center
    top_arm.movey(2.0) 
    
    # 3. Add Bottom Arm
    bot_arm = c << u_shaped_arm()
    # Mirror and shift Y down
    bot_arm.mirror()
    bot_arm.movey(-2.0)
    
    return c

# Generate and Save
device = full_device()
device.write_gds("device_optimized.gds")
# To see the result, open device_optimized.gds in KLayout.
# You will see the center gratings are distinct and the arms are curved paths.