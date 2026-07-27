import gdsfactory as gf
import numpy as np

# 1. Define a robust CrossSection
xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0), radius_min=2.0)

@gf.cell
def straight_with_gratings(length=20, side="bottom"):
    """
    Creates a straight waveguide with grating teeth on a specific side.
    """
    c = gf.Component()
    wg = c << gf.components.straight(length=length, cross_section=xs)
    c.add_port("o1", port=wg.ports["o1"])
    c.add_port("o2", port=wg.ports["o2"])

    # Grating Parameters
    tooth_w = 0.2
    tooth_l = 0.3
    period = 0.5
    num_teeth = int(length / period)
    
    y_offset = (0.5 / 2 + tooth_l / 2) if side == "top" else -(0.5 / 2 + tooth_l / 2)
    
    for i in range(num_teeth):
        x = (i * period) - (length / 2) + (period / 2)
        tooth = c << gf.components.rectangle(size=(tooth_w, tooth_l), layer=(1, 0))
        tooth.center = (x, y_offset)
        
    return c

@gf.cell
def device():
    c = gf.Component()
    
    # Gap between the coupled waveguides
    gap = 0.6 
    
    # --- Top Arm ---
    # Grating on bottom (side="bottom")
    top_straight = c << straight_with_gratings(length=20, side="bottom")
    top_straight.movey(gap / 2 + 0.25) # Offset for gap
    
    # U-turn on the right
    top_u = c << gf.components.bend_euler(radius=2.0, angle=180, cross_section=xs)
    top_u.connect("o1", top_straight.ports["o2"])
    
    # Taper/Outward bend on the left
    top_out = c << gf.components.bend_euler(radius=2.0, angle=-45, cross_section=xs)
    top_out.connect("o1", top_straight.ports["o1"])
    
    # --- Bottom Arm ---
    # Grating on top (side="top")
    bot_straight = c << straight_with_gratings(length=20, side="top")
    bot_straight.movey(-(gap / 2 + 0.25))
    
    # U-turn on the left
    bot_u = c << gf.components.bend_euler(radius=2.0, angle=-180, cross_section=xs)
    bot_u.connect("o1", bot_straight.ports["o1"])
    
    # Taper/Outward bend on the right
    bot_out = c << gf.components.bend_euler(radius=2.0, angle=45, cross_section=xs)
    bot_out.connect("o1", bot_straight.ports["o2"])
    
    return c

if __name__ == "__main__":
    c = device()
    # If using KLayout or a viewer, this will display the structure
    c.show() 
    c.write_gds("device.gds")
    print("Geometry generated successfully.")