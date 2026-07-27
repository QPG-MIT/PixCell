import gdsfactory as gf

@gf.cell
def directional_coupler(
    total_length: float = 18.0,
    total_height: float = 3.0,
    wg_width: float = 0.5,
    gap: float = 0.2,
    coupling_length: float = 6.0
):
    """
    Creates a symmetric directional coupler with a straight coupling region,
    matching the exact 18x3 footprint constraint.
    """
    c = gf.Component("directional_coupler")
    
    # KEY FIX: We explicitly set `radius=1.0` (or any value < 7.6) in the cross 
    # section. This tells GDSFactory's DRC engine to allow tighter S-bends.
    xs = gf.cross_section.cross_section(
        width=wg_width, 
        layer=(1, 0),
        radius=1.0  
    )

    # --- Footprint Calculations ---
    # Max/min Y coordinates to guarantee a 3.0 total height bounding box
    port_y = (total_height - wg_width) / 2.0  # ±1.25 µm
    
    # Waveguide centers at the straight coupling region
    center_y = (gap + wg_width) / 2.0         # ±0.35 µm
    
    # Calculate S-bend dimensions
    # Horizontal span (dx) splits the remaining length after the straight section
    dx = (total_length - coupling_length) / 2.0  # 6.0 µm
    # Vertical span (dy) is the difference between port Y and coupling region Y
    dy = port_y - center_y                       # 0.9 µm

    # --- Component Primitives ---
    # Downward/Upward S-bends and middle straight section
    sbend_down = gf.components.bend_s(size=(dx, -dy), cross_section=xs)
    sbend_up = gf.components.bend_s(size=(dx, dy), cross_section=xs)
    straight_mid = gf.components.straight(length=coupling_length, cross_section=xs)

    # --- Geometry Assembly ---
    # Top Arm Instances
    top_in = c << sbend_down
    top_str = c << straight_mid
    top_out = c << sbend_up

    # Bottom Arm Instances
    bot_in = c << sbend_up
    bot_str = c << straight_mid
    bot_out = c << sbend_down

    # Position the input S-bends
    top_in.move((0, port_y))
    bot_in.move((0, -port_y))

    # Connect Top Arm segments natively port-to-port
    top_str.connect("o1", top_in.ports["o2"])
    top_out.connect("o1", top_str.ports["o2"])

    # Connect Bottom Arm segments natively port-to-port
    bot_str.connect("o1", bot_in.ports["o2"])
    bot_out.connect("o1", bot_str.ports["o2"])

    # --- Expose External Ports ---
    # Left side (inputs)
    c.add_port("o1", port=top_in.ports["o1"])
    c.add_port("o2", port=bot_in.ports["o1"])
    # Right side (outputs)
    c.add_port("o3", port=top_out.ports["o2"])
    c.add_port("o4", port=bot_out.ports["o2"])

    return c

if __name__ == "__main__":
    # Create the device
    device = directional_coupler()
    
    # Write the GDS file
    device.write_gds("directional_coupler.gds")