import gdsfactory as gf

@gf.cell
def device():
    """
    Directional coupler with tuned proportions to match target image.
    Footprint: 120um x 4um.
    """
    c = gf.Component()
    
    # 1. Define Constraints & Parameters
    # Total device footprint
    L_total = 120.0
    H_footprint = 4.0
    
    # Waveguide geometry
    wg_width = 0.5
    gap = 0.2  # Gap between coupled waveguides
    
    # Longitudinal Segmentation Analysis based on Target Image:
    # - The central coupling region is the dominant feature (approx 50-60% of length).
    # - The S-bends are steeper/shorter than the coupling region.
    # - Input/Output straight leads are distinct but short.
    
    # Proposed segmentation:
    l_io = 8.0          # Short straight input/output sections
    l_coupling = 64.0   # Extended coupling region to match visual proportion
    
    # Calculate bend length based on remaining space
    # L_total = 2*l_io + 2*l_bend + l_coupling
    # 120 = 16 + 2*l_bend + 64
    # 2*l_bend = 40 => l_bend = 20.0
    l_bend = (L_total - l_coupling - 2 * l_io) / 2
    
    # Vertical Positioning
    # We constrain the outer ports to the edges of the 4um height.
    # Center Y of outer waveguide = (H - w) / 2
    y_outer_center = (H_footprint - wg_width) / 2  # 1.75 um
    
    # Center Y of inner coupled waveguide = (gap + w) / 2
    y_inner_center = (gap + wg_width) / 2          # 0.35 um
    
    # Vertical shift required for S-bend
    dy = y_outer_center - y_inner_center           # 1.4 um
    
    # Define Cross Section
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))

    # 2. Build Top Arm (Left to Right)
    # Start at top-left
    t_in = c << gf.components.straight(length=l_io, cross_section=xs)
    t_in.move((0, y_outer_center))
    
    # S-Bend downwards to coupling region
    t_bend_in = c << gf.components.bend_s(size=(l_bend, -dy), cross_section=xs)
    t_bend_in.connect("o1", t_in.ports["o2"])
    
    # Coupled straight section
    t_coup = c << gf.components.straight(length=l_coupling, cross_section=xs)
    t_coup.connect("o1", t_bend_in.ports["o2"])
    
    # S-Bend upwards to output
    t_bend_out = c << gf.components.bend_s(size=(l_bend, dy), cross_section=xs)
    t_bend_out.connect("o1", t_coup.ports["o2"])
    
    # Output straight section
    t_out = c << gf.components.straight(length=l_io, cross_section=xs)
    t_out.connect("o1", t_bend_out.ports["o2"])

    # 3. Build Bottom Arm (Left to Right)
    # Start at bottom-left
    b_in = c << gf.components.straight(length=l_io, cross_section=xs)
    b_in.move((0, -y_outer_center))
    
    # S-Bend upwards to coupling region
    b_bend_in = c << gf.components.bend_s(size=(l_bend, dy), cross_section=xs)
    b_bend_in.connect("o1", b_in.ports["o2"])
    
    # Coupled straight section
    b_coup = c << gf.components.straight(length=l_coupling, cross_section=xs)
    b_coup.connect("o1", b_bend_in.ports["o2"])
    
    # S-Bend downwards to output
    b_bend_out = c << gf.components.bend_s(size=(l_bend, -dy), cross_section=xs)
    b_bend_out.connect("o1", b_coup.ports["o2"])
    
    # Output straight section
    b_out = c << gf.components.straight(length=l_io, cross_section=xs)
    b_out.connect("o1", b_bend_out.ports["o2"])

    # 4. Expose Ports
    c.add_port("o1", port=t_in.ports["o1"])
    c.add_port("o2", port=b_in.ports["o1"])
    c.add_port("o3", port=t_out.ports["o2"])
    c.add_port("o4", port=b_out.ports["o2"])

    return c

if __name__ == "__main__":
    d = device()
    d.write_gds("directional_coupler.gds")