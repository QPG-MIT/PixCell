import gdsfactory as gf

@gf.cell
def recreated_device_v5():
    """
    Recreates the device with high fidelity.
    Corrects the bundle order (thick bar inside, thin lines outside)
    and refines geometry to match the target proportions.
    """
    c = gf.Component("recreated_device_v5")
    
    # --- Dimensions & Constraints ---
    L_MAX = 120.0
    H_MAX = 4.0
    layer = (1, 0)
    
    # Feature Dimensions
    w_thin = 0.04    # Fine lines
    w_thick = 0.6    # Central thick bars
    p_mid = 0.12     # Pitch for the 5 center lines
    p_bundle = 0.12  # Pitch for the 4 bundle lines
    r_bend = 1.5     # Bend radius for 'horns'
    l_bundle = 95.0  # Horizontal length of the bundle
    v_ext = 0.8      # Vertical horn extension
    
    # 1. Middle Group (5 straight thin lines)
    # Spans full width of the device.
    mid_xs = gf.cross_section.cross_section(width=w_thin, layer=layer)
    for i in range(-2, 3):
        m = c << gf.components.straight(length=L_MAX, cross_section=mid_xs)
        m.y = i * p_mid
        m.x = 0

    # 2. Bundle Construction (Top and Bottom)
    # The bundle consists of 1 thick bar (inside) and 4 thin lines (outside).
    def get_bundle_xs(is_top=True):
        sign = 1 if is_top else -1
        sections = []
        
        # Thick bar: placed closest to center
        # Inner edge at ~0.4um, so center is at 0.4 + 0.3 = 0.7
        sections.append(gf.cross_section.Section(width=w_thick, offset=sign * 0.7, layer=layer))
        
        # 4 Thin lines: placed outside the thick bar
        # Gap between bar and lines is 0.15um
        # Thick bar edge is at 0.7 + 0.3 = 1.0. First line at 1.15.
        base_offset = 1.15
        for i in range(4):
            sections.append(gf.cross_section.Section(
                width=w_thin, 
                offset=sign * (base_offset + i * p_bundle), 
                layer=layer
            ))
        
        return gf.cross_section.cross_section(sections=sections, radius_min=0.5)

    def add_bundle_assembly(is_top=True):
        sign = 1 if is_top else -1
        xs = get_bundle_xs(is_top=is_top)
        
        # Horizontal section
        main = c << gf.components.straight(length=l_bundle, cross_section=xs)
        main.x = 0
        main.y = 0 # Offsets are handled in the CrossSection
        
        # Right Horn: Bend 90 deg AWAY from center, then straight
        br = c << gf.components.bend_euler(radius=r_bend, angle=90 * sign, cross_section=xs)
        br.connect("o1", main.ports["o2"])
        er = c << gf.components.straight(length=v_ext, cross_section=xs)
        er.connect("o1", br.ports["o2"])
        
        # Left Horn: Bend -90 deg AWAY from center, then straight
        bl = c << gf.components.bend_euler(radius=r_bend, angle=-90 * sign, cross_section=xs)
        bl.connect("o1", main.ports["o1"])
        el = c << gf.components.straight(length=v_ext, cross_section=xs)
        el.connect("o1", bl.ports["o2"])

    # Add Top and Bottom bundles
    add_bundle_assembly(is_top=True)
    add_bundle_assembly(is_top=False)

    # Final Centering
    c.center = (0, 0)
    return c

if __name__ == "__main__":
    device = recreated_device_v5()
    device.write_gds("recreated_device_v5.gds")
    device.show()