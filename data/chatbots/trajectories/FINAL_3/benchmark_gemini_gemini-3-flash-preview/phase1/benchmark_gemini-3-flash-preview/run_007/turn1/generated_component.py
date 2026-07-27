import gdsfactory as gf

@gf.cell
def directional_coupler_recreated():
    """
    Recreates the directional coupler from the reference image.
    Footprint target: 120um x 4um
    """
    c = gf.Component("directional_coupler")
    
    # --- 1. Design Parameters ---
    # Width = 0.5um
    # To reach total height of 4um: 
    # Max top edge = 2.0, Max bottom edge = -2.0
    # Center of top outer waveguide = 2.0 - 0.25 = 1.75
    # Center of bottom outer waveguide = -2.0 + 0.25 = -1.75
    
    # To reach central gap of 0.2um:
    # Center of top inner waveguide = 0.1 + 0.25 = 0.35
    # Center of bottom inner waveguide = -0.1 - 0.25 = -0.35
    
    # dy for bend_s = 1.75 - 0.35 = 1.4um
    
    w = 0.5
    gap = 0.2
    dy = 1.4
    
    # Total length = 120um. 
    # Allocating 40um for left bends, 40um for center, 40um for right bends.
    dx = 40.0
    l_center = 40.0
    
    xs = gf.cross_section.cross_section(width=w, layer=(1, 0))
    
    # --- 2. Instantiate Parametric Primitives ---
    # Central coupling region
    middle = gf.components.coupler_straight(length=l_center, gap=gap, cross_section=xs)
    # S-bend for transitions
    s_bend = gf.components.bend_s(size=(dx, dy), cross_section=xs)
    
    # --- 3. Assembly ---
    mid_ref = c << middle
    
    # Left Side
    bl_bend = c << s_bend
    bl_bend.connect("o2", mid_ref.ports["o1"])
    
    tl_bend = c << s_bend
    tl_bend.mirror(p1=(0, 0), p2=(1, 0))
    tl_bend.connect("o2", mid_ref.ports["o2"])
    
    # Right Side
    tr_bend = c << s_bend
    tr_bend.mirror(p1=(0, 0), p2=(1, 0))
    tr_bend.connect("o1", mid_ref.ports["o3"])
    
    br_bend = c << s_bend
    br_bend.connect("o1", mid_ref.ports["o4"])
    
    # --- 4. Ports ---
    c.add_port("o1", port=bl_bend.ports["o1"])
    c.add_port("o2", port=tl_bend.ports["o1"])
    c.add_port("o3", port=tr_bend.ports["o2"])
    c.add_port("o4", port=br_bend.ports["o2"])
    
    return c

if __name__ == "__main__":
    # Create the component
    device = directional_coupler_recreated()
    
    # Write to GDS file (Crucial for output)
    device.write_gds("directional_coupler.gds")
    
    # Print dimensions for verification
    # dxsize and dysize are the properties in current GDSFactory/KFactory
    print(f"Dimensions: {device.dxsize:.2f} um x {device.dysize:.2f} um")