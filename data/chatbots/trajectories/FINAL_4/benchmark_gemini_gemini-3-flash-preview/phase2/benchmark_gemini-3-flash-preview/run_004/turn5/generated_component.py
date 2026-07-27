import gdsfactory as gf

@gf.cell
def directional_coupler_final():
    """
    Directional coupler matching the target image proportions and footprint.
    Footprint: 18um x 3um.
    
    Fix: Added 'radius' to the cross_section to allow tight S-bends.
    """
    c = gf.Component("directional_coupler_v5_fixed")
    
    # 1. Design Parameters
    L_total = 18.0
    H_total = 3.0
    w = 0.5         # Waveguide width
    gap = 0.2       # Clear gap at the coupling region
    
    # Proportions: Long waist and smooth transitions
    L_waist = 8.0   
    L_sbend = (L_total - L_waist) / 2 # 5.0 um per transition
    
    # Vertical coordinates for centers
    # At edges: reaches the boundary (H_total/2)
    y_start = H_total / 2 - w / 2    # 1.25
    # At waist: centered around 0
    y_waist = gap / 2 + w / 2        # 0.1 + 0.25 = 0.35
    dy = y_start - y_waist           # 0.9 vertical offset
    
    # IMPORTANT: Set radius to 2.0 to bypass the default 10.0 radius check
    xs = gf.cross_section.cross_section(width=w, layer=(1, 0), radius=2.0)
    
    # 2. Build Top Waveguide
    # First S-bend (Input to Waist)
    t1 = c << gf.components.bend_s(size=(L_sbend, -dy), cross_section=xs)
    # Align to the left edge and top y_start
    t1.movex(-L_total / 2)
    t1.movey(y_start)
    
    # Straight coupling section
    t2 = c << gf.components.straight(length=L_waist, cross_section=xs)
    t2.connect("o1", t1.ports["o2"])
    
    # Second S-bend (Waist to Output)
    t3 = c << gf.components.bend_s(size=(L_sbend, dy), cross_section=xs)
    t3.connect("o1", t2.ports["o2"])
    
    # 3. Build Bottom Waveguide (Symmetric mirror)
    # First S-bend
    b1 = c << gf.components.bend_s(size=(L_sbend, dy), cross_section=xs)
    b1.movex(-L_total / 2)
    b1.movey(-y_start)
    
    # Straight coupling section
    b2 = c << gf.components.straight(length=L_waist, cross_section=xs)
    b2.connect("o1", b1.ports["o2"])
    
    # Second S-bend
    b3 = c << gf.components.bend_s(size=(L_sbend, -dy), cross_section=xs)
    b3.connect("o1", b2.ports["o2"])
    
    # 4. Define Ports
    c.add_port("o1", port=t1.ports["o1"])
    c.add_port("o2", port=b1.ports["o1"])
    c.add_port("o3", port=t3.ports["o2"])
    c.add_port("o4", port=b3.ports["o2"])
    
    return c

if __name__ == "__main__":
    component = directional_coupler_final()
    # Verification of footprint (should be 18.0 x 3.0)
    print(f"Final Footprint: {component.dxsize:.2f}um x {component.dysize:.2f}um")
    component.write_gds("directional_coupler_final.gds")
    component.show()