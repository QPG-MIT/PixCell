import gdsfactory as gf

@gf.cell
def photonic_taper_device():
    """
    Recreates the device geometry based on the provided image and footprint.
    Footprint: 120um x 4um
    """
    c = gf.Component("multi_rail_taper")
    
    # Parameters derived from footprint and visual analysis
    length = 120.0
    w_line = 0.06     # Width of the thin waveguide lines
    g_line = 0.07     # Gap between thin lines
    w_slab = 0.35     # Width of the thick slab waveguide
    g_slab_rail = 0.1 # Gap between the slab and the rail groups
    
    # Layer definition
    layer = (1, 0)
    
    # Define cross-sections
    xs_line = gf.cross_section.cross_section(width=w_line, layer=layer)
    xs_slab = gf.cross_section.cross_section(width=w_slab, layer=layer)
    
    # 1. Create Central Straight Group (5 lines)
    # This group is centered at y=0 and spans the full 120um
    for i in range(5):
        y_offset = (i - 2) * (w_line + g_line)
        line = c << gf.components.straight(length=length, cross_section=xs_line)
        line.x = 0
        line.y = y_offset

    # 2. Create Curved Top and Bottom Complexes
    # We define a single 'half' component and mirror it to ensure perfect symmetry.
    @gf.cell
    def rail_complex_half():
        hc = gf.Component()
        
        # Define the base path for the complex: flat in the middle, curving up at ends.
        # Points: [(-60, 1.2), (-40, 0.6), (40, 0.6), (60, 1.2)]
        # This fits within the 4um height (y max ~2.0)
        p = gf.Path([(-60, 1.3), (-35, 0.65), (35, 0.65), (60, 1.3)])
        p_smooth = gf.path.smooth(p, radius=15)
        
        # Add the slab waveguide following the path
        hc << gf.path.extrude(p_smooth, cross_section=xs_slab)
        
        # Add 5 thin waveguides above the slab
        # They follow the same path but are vertically offset
        for i in range(5):
            # Calculate offset from the path center (center of the slab)
            # Offset = half_slab + gap + half_rail_group + individual_offset
            base_offset = (w_slab / 2) + g_slab_rail + (w_line / 2)
            y_offset_from_path = base_offset + (i * (w_line + g_line))
            
            line = hc << gf.path.extrude(p_smooth, cross_section=xs_line)
            line.movey(y_offset_from_path)
            
        return hc

    # Add the top half
    top_half = c << rail_complex_half()
    
    # Add the bottom half by mirroring the top half across the X-axis
    bottom_half = c << rail_complex_half()
    bottom_half.mirror(p1=(0, 0), p2=(1, 0))
    
    # Center the entire component to fit the 120x4 footprint perfectly
    c.x = 0
    c.y = 0
    
    return c

if __name__ == "__main__":
    # Create the component
    component = photonic_taper_device()
    
    # Export to GDS
    component.write_gds("photonic_device.gds")
    
    # Optional: Display the component (requires a viewer like KLayout)
    # component.show()