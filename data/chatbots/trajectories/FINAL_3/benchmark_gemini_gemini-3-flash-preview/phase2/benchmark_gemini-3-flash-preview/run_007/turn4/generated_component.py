import gdsfactory as gf

@gf.cell
def directional_coupler_refined():
    """
    Recreates the directional coupler with tighter transitions to match the target.
    
    Target Footprint: 120um x 4um
    - Central section: ~40% of length
    - Transitions: Compact (sharp curvature)
    - Arms: Long and parallel
    """
    c = gf.Component("directional_coupler")
    
    # --- 1. Dimensions & Constraints ---
    total_length = 120.0
    total_height = 4.0
    w = 0.5      # Standard waveguide width
    gap = 0.2    # Coupling gap in the center
    
    # Precise vertical offset calculation:
    # To fit in a 4um height: 
    #   Outer arm center is at +/- (4.0/2 - 0.5/2) = +/- 1.75
    #   Inner arm center is at +/- (0.2/2 + 0.5/2) = +/- 0.35
    #   Total vertical shift required: 1.75 - 0.35 = 1.4 um
    dy = 1.4 
    
    # Horizontal allocation (Total must be 120.0)
    # Reducing l_bend makes the curves "snappier" like the reference image.
    l_bend = 12.0          
    l_coupler = 46.0       
    l_straight = (total_length - l_coupler - 2 * l_bend) / 2 # ~25.0 um
    
    xs = gf.cross_section.cross_section(width=w, layer=(1, 0))
    
    # --- 2. Create Primitives ---
    coupler = gf.components.coupler_straight(length=l_coupler, gap=gap, cross_section=xs)
    # bend_s creates the characteristic S-curve; reducing size[0] increases curvature
    s_bend = gf.components.bend_s(size=(l_bend, dy), cross_section=xs)
    end_straight = gf.components.straight(length=l_straight, cross_section=xs)
    
    # --- 3. Assembly ---
    # Central Coupling Region
    mid = c << coupler
    
    # Left Side (Input)
    bl_bend = c << s_bend
    bl_bend.connect("o2", mid.ports["o1"])
    bl_ext = c << end_straight
    bl_ext.connect("o2", bl_bend.ports["o1"])
    
    tl_bend = c << s_bend
    tl_bend.mirror(p1=(0, 0), p2=(1, 0))
    tl_bend.connect("o2", mid.ports["o2"])
    tl_ext = c << end_straight
    tl_ext.connect("o2", tl_bend.ports["o1"])
    
    # Right Side (Output)
    tr_bend = c << s_bend
    tr_bend.connect("o1", mid.ports["o3"])
    tr_ext = c << end_straight
    tr_ext.connect("o1", tr_bend.ports["o2"])
    
    # Mirror the bottom-right bend vertically
    br_bend = c << s_bend
    br_bend.mirror(p1=(0, 0), p2=(1, 0))
    br_bend.connect("o1", mid.ports["o4"])
    br_ext = c << end_straight
    br_ext.connect("o1", br_bend.ports["o2"])
    
    # --- 4. Define External Ports ---
    c.add_port("o1", port=bl_ext.ports["o1"])
    c.add_port("o2", port=tl_ext.ports["o1"])
    c.add_port("o3", port=tr_ext.ports["o2"])
    c.add_port("o4", port=br_ext.ports["o2"])
    
    return c

if __name__ == "__main__":
    device = directional_coupler_refined()
    
    # Verification of constraints
    print(f"Footprint: {device.dxsize:.2f} um x {device.dysize:.2f} um")
    
    # Save and Show
    device.write_gds("directional_coupler_final.gds")
    device.show()