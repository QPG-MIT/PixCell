import gdsfactory as gf

# 1. Define a custom cross-section with a small radius_min.
# This prevents the ValueError: min_bend_radius < CrossSection.radius_min
xs = gf.cross_section.cross_section(
    width=0.4, 
    layer=(1, 0), 
    radius_min=0.5
)

@gf.cell
def custom_device():
    c = gf.Component()

    # --- 1. Outer Racetrack Loop ---
    # Dimensions: 3.0um (height) x 5.5um (width)
    # Radius = 1.5um (Height = 2 * Radius)
    # Straight length = Width - (2 * Radius) = 5.5 - 3.0 = 2.5um
    
    r = 1.5
    straight_len = 2.5
    
    # Create primitives using the custom cross-section
    s_top = c << gf.components.straight(length=straight_len, cross_section=xs)
    s_bot = c << gf.components.straight(length=straight_len, cross_section=xs)
    
    # We use 4 Euler bends to form the loop
    b1 = c << gf.components.bend_euler(radius=r, angle=90, cross_section=xs)
    b2 = c << gf.components.bend_euler(radius=r, angle=90, cross_section=xs)
    b3 = c << gf.components.bend_euler(radius=r, angle=90, cross_section=xs)
    b4 = c << gf.components.bend_euler(radius=r, angle=90, cross_section=xs)

    # Assemble the loop (Connect ports)
    # Top straight to bends
    b1.connect("o1", s_top.ports["o1"])
    b2.connect("o1", s_top.ports["o2"])
    
    # Bottom straight to bends
    s_bot.connect("o1", b1.ports["o2"])
    b3.connect("o1", s_bot.ports["o2"])
    b4.connect("o1", b2.ports["o2"])
    
    # Close the loop
    b3.connect("o2", b4.ports["o2"])

    # --- 2. Inner Structures ---
    # Two rectangular blocks
    rect_width = 0.8
    rect_height = 1.2
    
    rect_l = c << gf.components.rectangle(size=(rect_width, rect_height), layer=(1, 0), centered=True)
    rect_r = c << gf.components.rectangle(size=(rect_width, rect_height), layer=(1, 0), centered=True)
    
    rect_l.movex(-0.7)
    rect_r.movex(0.7)
    
    # Bridges (central connections)
    bridge_size = (0.4, 0.4)
    bridge_top = c << gf.components.rectangle(size=bridge_size, layer=(1, 0), centered=True)
    bridge_bot = c << gf.components.rectangle(size=bridge_size, layer=(1, 0), centered=True)
    
    bridge_top.movey(0.6)
    bridge_bot.movey(-0.6)

    return c

# Run the component generation and save the GDS file
if __name__ == "__main__":
    device = custom_device()
    # Write the GDS file explicitly
    device.write_gds("custom_device.gds")
    print("GDS file 'custom_device.gds' produced successfully.")