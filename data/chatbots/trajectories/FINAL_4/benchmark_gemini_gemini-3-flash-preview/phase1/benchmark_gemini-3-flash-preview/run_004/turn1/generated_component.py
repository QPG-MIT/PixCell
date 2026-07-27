import gdsfactory as gf

@gf.cell
def recreated_device():
    """
    Recreates the symmetric curved waveguide geometry from the image.
    Footprint: 18um (width) x 3um (height).
    
    The device consists of two waveguides that converge at the center.
    Each waveguide is formed by two back-to-back S-bends.
    """
    c = gf.Component("curved_coupler")
    
    # 1. Define Geometry Parameters
    L = 18.0  # Total length
    H = 3.0   # Total height
    w = 0.5   # Waveguide width
    gap = 0.2 # Minimum gap between waveguides at the center
    
    # Calculate dimensions for the S-bend primitives
    # Each S-bend covers half the total length (9um)
    dx = L / 2
    
    # Vertical offset calculation:
    # Waveguide center at the ends: +/- (H/2 - w/2) = +/- 1.25 um
    # Waveguide center at the middle: +/- (gap/2 + w/2) = +/- 0.35 um
    # Vertical travel for one S-bend (dy) = 1.25 - 0.35 = 0.9 um
    dy = (H / 2 - w / 2) - (gap / 2 + w / 2)
    
    # 2. Define Cross-Section
    xs = gf.cross_section.cross_section(width=w, layer=(1, 0))
    
    # 3. Construct Top Waveguide
    # Moves from outer top edge down toward the center gap
    top_left = c << gf.components.bend_s(size=(dx, -dy), cross_section=xs)
    top_left.move((-L/2, H/2 - w/2)) # Start at the top-left boundary
    
    # Moves from center gap back up to outer top edge
    top_right = c << gf.components.bend_s(size=(dx, dy), cross_section=xs)
    top_right.connect("o1", top_left.ports["o2"])
    
    # 4. Construct Bottom Waveguide
    # Moves from outer bottom edge up toward the center gap
    bot_left = c << gf.components.bend_s(size=(dx, dy), cross_section=xs)
    bot_left.move((-L/2, -(H/2 - w/2))) # Start at the bottom-left boundary
    
    # Moves from center gap back down to outer bottom edge
    bot_right = c << gf.components.bend_s(size=(dx, -dy), cross_section=xs)
    bot_right.connect("o1", bot_left.ports["o2"])
    
    # 5. Add External Ports
    c.add_port("o1", port=top_left.ports["o1"])
    c.add_port("o2", port=bot_left.ports["o1"])
    c.add_port("o3", port=top_right.ports["o2"])
    c.add_port("o4", port=bot_right.ports["o2"])
    
    return c

if __name__ == "__main__":
    # Create the component
    device = recreated_device()
    
    # Explicitly write the GDS file to disk
    device.write_gds("recreated_device.gds")
    
    # Print dimensions for verification
    # Using modern kfactory/gdsfactory attributes
    try:
        print(f"Device Footprint: {device.dxsize:.2f} um x {device.dysize:.2f} um")
    except AttributeError:
        # Fallback for older gdsfactory versions
        bbox = device.bbox()
        w_fb = bbox[1][0] - bbox[0][0]
        h_fb = bbox[1][1] - bbox[0][1]
        print(f"Device Footprint: {w_fb:.2f} um x {h_fb:.2f} um")