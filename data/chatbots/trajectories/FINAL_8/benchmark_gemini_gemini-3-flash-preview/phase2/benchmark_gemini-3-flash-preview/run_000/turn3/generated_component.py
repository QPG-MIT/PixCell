import gdsfactory as gf

@gf.cell
def recreated_device():
    """
    Recreates the device with improved fidelity for the 120x4um footprint.
    Sets radius_min to allow for the sharp bends required by the small footprint.
    """
    c = gf.Component("recreated_device_v4")
    
    # --- Constraints & Layer ---
    L_MAX = 120.0
    H_MAX = 4.0
    layer = (1, 0)
    
    # --- Visual Parameters ---
    w_thin = 0.04   
    w_thick = 0.55  
    pitch_mid = 0.15 
    r_bend = 0.3    # Small radius for the "horns"
    
    # 1. Middle Group (5 straight thin lines)
    # Spans the full width
    mid_xs = gf.cross_section.cross_section(width=w_thin, layer=layer)
    for i in range(-2, 3):
        m = c << gf.components.straight(length=L_MAX, cross_section=mid_xs)
        m.y = i * pitch_mid
        m.x = 0

    # 2. Side Bundles (Top and Bottom "Horn" Assemblies)
    # We define the offsets for 1 thick bar + 4 thin lines.
    bundle_offsets = [0, 0.45, 0.57, 0.69, 0.81] 
    bundle_widths = [w_thick, w_thin, w_thin, w_thin, w_thin]
    
    def get_bundle_xs(is_top=True):
        sign = 1 if is_top else -1
        sections = []
        for w, o in zip(bundle_widths, bundle_offsets):
            sections.append(gf.cross_section.Section(width=w, offset=sign*o, layer=layer))
        
        # KEY FIX: Set radius_min to be equal to or smaller than our intended r_bend
        return gf.cross_section.cross_section(sections=sections, radius_min=r_bend)

    # Path geometry for the side bundles
    l_side_straight = 85.0  # Length of the horizontal part
    v_ext = 0.6             # Length of the vertical tips
    
    def add_bundle(y_offset, is_top=True):
        sign = 1 if is_top else -1
        xs = get_bundle_xs(is_top=is_top)
        
        # Main horizontal section
        main = c << gf.components.straight(length=l_side_straight, cross_section=xs)
        main.y = y_offset
        main.x = 0
        
        # Right Side: Bend up/down then straight extension
        br = c << gf.components.bend_euler(radius=r_bend, angle=90 * sign, cross_section=xs)
        br.connect("o1", main.ports["o2"])
        er = c << gf.components.straight(length=v_ext, cross_section=xs)
        er.connect("o1", br.ports["o2"])
        
        # Left Side: Bend up/down then straight extension
        bl = c << gf.components.bend_euler(radius=r_bend, angle=-90 * sign, cross_section=xs)
        bl.connect("o1", main.ports["o1"])
        el = c << gf.components.straight(length=v_ext, cross_section=xs)
        el.connect("o1", bl.ports["o2"])

    # Position side bundles with clear gaps from the middle group
    # y=0.8 and y=-0.8 centers the thick bars well away from the center 5 lines
    add_bundle(y_offset=0.8, is_top=True)
    add_bundle(y_offset=-0.8, is_top=False)

    # Center the entire assembly at (0,0)
    c.center = (0, 0)
    return c

if __name__ == "__main__":
    device = recreated_device()
    # Write GDS and show
    device.write_gds("recreated_device_v4.gds")
    device.show()