import gdsfactory as gf

@gf.cell
def directional_coupler_recreation():
    """
    Recreates the symmetric directional coupler from the reference image.
    Footprint target: 120um x 4um
    """
    c = gf.Component("directional_coupler")
    
    # 1. Define common parameters
    layer = (1, 0)
    width = 0.5
    gap = 0.2
    # Create a standard strip cross-section
    xs = gf.cross_section.cross_section(width=width, layer=layer)
    
    # Length budget (Total 120um)
    l_coupler = 60
    l_sbend = 20
    l_ext = 10
    
    # Height budget (Total 4um)
    # Centers at ends: +/- 1.75 (so edges are +/- 2.0)
    # Centers at coupler: +/- (gap/2 + width/2) = +/- (0.1 + 0.25) = +/- 0.35
    dy = 1.4  # 1.75 - 0.35
    
    # 2. Central coupling section
    # This primitive creates two parallel waveguides
    coupler = c << gf.components.coupler_straight(
        length=l_coupler, 
        gap=gap, 
        cross_section=xs
    )
    
    # 3. S-Bend transitions
    # Connecting the narrow coupling region to the wide-spaced ports
    sb_tl = c << gf.components.bend_s(size=(l_sbend, dy), cross_section=xs)
    sb_tl.connect("o2", coupler.ports["o2"])
    
    sb_bl = c << gf.components.bend_s(size=(l_sbend, -dy), cross_section=xs)
    sb_bl.connect("o2", coupler.ports["o1"])
    
    sb_tr = c << gf.components.bend_s(size=(l_sbend, dy), cross_section=xs)
    sb_tr.connect("o1", coupler.ports["o3"])
    
    sb_br = c << gf.components.bend_s(size=(l_sbend, -dy), cross_section=xs)
    sb_br.connect("o1", coupler.ports["o4"])
    
    # 4. Straight Input/Output extensions
    ext = gf.components.straight(length=l_ext, cross_section=xs)
    
    ext_tl = c << ext
    ext_tl.connect("o2", sb_tl.ports["o1"])
    
    ext_bl = c << ext
    ext_bl.connect("o2", sb_bl.ports["o1"])
    
    ext_tr = c << ext
    ext_tr.connect("o1", sb_tr.ports["o2"])
    
    ext_br = c << ext
    ext_br.connect("o1", sb_br.ports["o2"])
    
    # 5. Define external ports
    c.add_port("o1", port=ext_bl.ports["o1"])
    c.add_port("o2", port=ext_tl.ports["o1"])
    c.add_port("o3", port=ext_tr.ports["o2"])
    c.add_port("o4", port=ext_br.ports["o2"])

    return c

if __name__ == "__main__":
    # Instantiate the component
    component = directional_coupler_recreation()
    
    # Produce the GDS file
    filename = "directional_coupler.gds"
    component.write_gds(filename)
    
    # Robustly calculate size for printing (handles KFactory/GDSFactory 7 & 8)
    try:
        # Standard GDSFactory properties
        w = component.xsize
        h = component.ysize
    except AttributeError:
        # KFactory specific fallback
        bbox = component.dbbox()
        w = bbox.width()
        h = bbox.height()
        
    print(f"Successfully saved: {filename}")
    print(f"Measured Footprint: {w:.2f} um x {h:.2f} um")