import gdsfactory as gf

@gf.cell
def directional_coupler_4x240():
    """
    Recreation of the directional coupler image.
    Constraint: Footprint 4um (height) x 240um (length).
    """
    c = gf.Component()

    # --- 1. Define Dimensions & Cross Section ---
    total_length = 240.0
    total_height = 4.0
    
    # Standard photonics values
    wg_width = 0.5
    gap = 0.2
    
    # --- Y-Axis Calculations ---
    # Center of the outer input/output waveguides to fit in 4um height:
    # Top edge = +2.0, Bottom edge = -2.0
    # Center = Edge - (Width/2)
    y_outer_top = (total_height / 2) - (wg_width / 2)  # 2.0 - 0.25 = 1.75
    
    # Center of the inner coupling waveguides:
    # Gap center is 0. Top waveguide center is (gap/2) + (width/2)
    y_inner_top = (gap / 2) + (wg_width / 2)           # 0.1 + 0.25 = 0.35
    
    # Vertical shift (dy) required for the S-bends
    dy = y_outer_top - y_inner_top                     # 1.75 - 0.35 = 1.4

    # --- X-Axis Calculations ---
    # We apportion the 240um length. 
    # Visually, the straight coupler is a significant chunk.
    length_coupling = 100.0
    # The remaining length is split between input and output bends
    length_sbend = (total_length - length_coupling) / 2  # (240 - 100)/2 = 70.0

    # Cross Section
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))

    # --- 2. Create Primitives ---
    
    # Central Straight Coupler
    # Creates two parallel waveguides
    coupler = c << gf.components.coupler_straight(
        length=length_coupling,
        gap=gap,
        cross_section=xs
    )

    # S-Bend Primitive
    # Create a generic S-bend going from (0,0) to (length, dy)
    s_bend_ref = gf.components.bend_s(
        size=(length_sbend, dy),
        cross_section=xs
    )

    # --- 3. Assembly (Connect Primitives) ---

    # Top Left Input
    # We mirror the S-bend in Y so it curves DOWN into the coupler.
    tl = c << s_bend_ref
    tl.mirror_y()
    # Connect the end of the bend (o2) to the coupler input (o1)
    tl.connect("o2", coupler.ports["o1"])

    # Bottom Left Input
    # Standard S-bend curves UP into the coupler.
    bl = c << s_bend_ref
    bl.connect("o2", coupler.ports["o2"])

    # Top Right Output
    # Standard S-bend curves UP away from the coupler.
    tr = c << s_bend_ref
    tr.connect("o1", coupler.ports["o3"])

    # Bottom Right Output
    # Mirror S-bend in Y to curve DOWN away from the coupler.
    br = c << s_bend_ref
    br.mirror_y()
    br.connect("o1", coupler.ports["o4"])

    # --- 4. Expose External Ports ---
    c.add_port("o1", port=tl.ports["o1"])
    c.add_port("o2", port=bl.ports["o1"])
    c.add_port("o3", port=tr.ports["o2"])
    c.add_port("o4", port=br.ports["o2"])

    return c

if __name__ == "__main__":
    # Generate the device
    device = directional_coupler_4x240()
    
    # Write the GDS file to disk
    gds_path = device.write_gds("directional_coupler_4x240.gds")
    
    # Validation Output
    print(f"GDS file successfully created at: {gds_path}")
    print(f"Device Footprint: {device.size_info.width} um x {device.size_info.height} um")