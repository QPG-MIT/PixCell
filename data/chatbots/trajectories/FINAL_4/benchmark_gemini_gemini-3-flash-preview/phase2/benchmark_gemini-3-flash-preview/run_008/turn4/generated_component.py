import gdsfactory as gf

@gf.cell
def directional_coupler_final(
    length: float = 18.0,
    total_height: float = 3.0,
    coupling_length: float = 4.5,
    wg_width: float = 0.54,
    gap: float = 0.18,
    layer: tuple = (1, 0),
) -> gf.Component:
    """
    Creates a directional coupler matching the 18x3um footprint.
    Fixed radius_min constraint to allow compact adiabatic transitions.
    
    Args:
        length: Total footprint length (um).
        total_height: Total footprint height (um).
        coupling_length: Length of the straight parallel section in the middle.
        wg_width: Waveguide width.
        gap: Minimum gap in the coupling region.
        layer: GDS layer.
    """
    c = gf.Component("directional_coupler_final")
    
    # 1. Geometry Calculations
    # Calculate horizontal length of each S-bend transition
    side_length = (length - coupling_length) / 2
    
    # Vertical positions to satisfy exactly total_height footprint:
    # Top edge of top rail at input/output = total_height / 2
    y_outer_center = (total_height / 2) - (wg_width / 2)
    # Center of rail in coupling region
    y_inner_center = (gap / 2) + (wg_width / 2)
    
    # Vertical displacement for the S-bend
    dy = y_inner_center - y_outer_center
    
    # 2. Define Cross-Section
    # FIX: Explicitly set radius_min to 1.0 to allow the small S-bends 
    # required for a 18um device length.
    xs = gf.cross_section.cross_section(
        width=wg_width, 
        layer=layer, 
        radius_min=1.0
    )
    
    # 3. Create Primitives
    # bend_s creates a smooth Euler-spiral transition (adiabatic curvature)
    s_bend = gf.components.bend_s(size=(side_length, dy), cross_section=xs)
    straight_mid = gf.components.straight(length=coupling_length, cross_section=xs)
    
    # 4. Assembly
    # --- Top Rail ---
    t_in = c << s_bend
    t_in.movey(y_outer_center)
    
    t_mid = c << straight_mid
    t_mid.connect("o1", t_in.ports["o2"])
    
    t_out = c << s_bend
    t_out.mirror_x()
    t_out.connect("o1", t_mid.ports["o2"])
    
    # --- Bottom Rail ---
    # Mirrored version of the top rail
    b_in = c << s_bend
    b_in.mirror_y()
    b_in.movey(-y_outer_center)
    
    b_mid = c << straight_mid
    b_mid.connect("o1", b_in.ports["o2"])
    
    b_out = c << s_bend
    b_out.mirror_y()
    b_out.mirror_x()
    b_out.connect("o1", b_mid.ports["o2"])
    
    # 5. Define Ports
    c.add_port("o1", port=t_in.ports["o1"])
    c.add_port("o2", port=b_in.ports["o1"])
    c.add_port("o3", port=t_out.ports["o2"])
    c.add_port("o4", port=b_out.ports["o2"])
    
    return c

if __name__ == "__main__":
    # Generate the component with tuned parameters for visual matching
    component = directional_coupler_final()
    
    # Print footprint verification
    print(f"Generated Footprint: {component.dxsize:.2f}um x {component.dysize:.2f}um")
    
    # Save and view
    component.write_gds("directional_coupler.gds")
    component.show()