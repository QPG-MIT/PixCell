import gdsfactory as gf

@gf.cell
def recreate_coupler_device():
    """
    Recreates the directional coupler geometry from the image.
    Footprint: 120um x 4um
    """
    c = gf.Component("directional_coupler_recreation")
    
    # Parameters derived to meet the [120, 4] footprint
    w = 0.5           # Waveguide width
    l_lead = 20.0     # Length of the outer straight leads
    dx_s = 20.0       # Horizontal length of the S-bends
    l_coupler = 40.0  # Length of the central coupling region
    gap = 0.2         # Gap between waveguides in the center
    
    # Total Length = l_lead(left) + dx_s(left) + l_coupler + dx_s(right) + l_lead(right)
    # Total Length = 20 + 20 + 40 + 20 + 20 = 120um
    
    # Define cross section
    xs = gf.cross_section.cross_section(width=w, layer=(1, 0))
    
    # Vertical footprint calculation:
    # Inner waveguide centers at +/- (gap/2 + width/2) = +/- (0.1 + 0.25) = +/- 0.35
    # Desired outer footprint edge is at +/- 2.0 (for total height of 4.0)
    # Desired outer waveguide center is at +/- (2.0 - width/2) = +/- 1.75
    # dy_s = abs(target_center - starting_center) = 1.75 - 0.35 = 1.4
    dy_s = 1.4
    
    # 1. Create the central coupling region
    coupler = c << gf.components.coupler_straight(length=l_coupler, gap=gap, cross_section=xs)
    
    # 2. Add Right-side transitions
    # Top-right S-bend and lead
    s_tr = c << gf.components.bend_s(size=(dx_s, dy_s), cross_section=xs)
    s_tr.connect("o1", coupler.ports["o3"])
    l_tr = c << gf.components.straight(length=l_lead, cross_section=xs)
    l_tr.connect("o1", s_tr.ports["o2"])
    
    # Bottom-right S-bend and lead
    s_br = c << gf.components.bend_s(size=(dx_s, -dy_s), cross_section=xs)
    s_br.connect("o1", coupler.ports["o4"])
    l_br = c << gf.components.straight(length=l_lead, cross_section=xs)
    l_br.connect("o1", s_br.ports["o2"])
    
    # 3. Add Left-side transitions
    # Top-left S-bend and lead
    s_tl = c << gf.components.bend_s(size=(dx_s, -dy_s), cross_section=xs)
    s_tl.connect("o1", coupler.ports["o2"])
    l_tl = c << gf.components.straight(length=l_lead, cross_section=xs)
    l_tl.connect("o2", s_tl.ports["o2"])
    
    # Bottom-left S-bend and lead
    s_bl = c << gf.components.bend_s(size=(dx_s, dy_s), cross_section=xs)
    s_bl.connect("o1", coupler.ports["o1"])
    l_bl = c << gf.components.straight(length=l_lead, cross_section=xs)
    l_bl.connect("o2", s_bl.ports["o2"])
    
    # Expose external ports
    c.add_port("o1", port=l_bl.ports["o1"])
    c.add_port("o2", port=l_tl.ports["o1"])
    c.add_port("o3", port=l_tr.ports["o2"])
    c.add_port("o4", port=l_br.ports["o2"])
    
    return c

if __name__ == "__main__":
    component = recreate_coupler_device()
    # Corrected attribute access for dimensions
    print(f"Component created with size: {component.xsize} um (width) x {component.ysize} um (height)")
    # component.show()