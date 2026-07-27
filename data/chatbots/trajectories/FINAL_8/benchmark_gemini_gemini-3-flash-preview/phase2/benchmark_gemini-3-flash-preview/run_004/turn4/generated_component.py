import gdsfactory as gf

@gf.cell
def device_geometry_turn4():
    """
    Creates a device with a 5-line central bus and two U-shaped superstructures.
    The superstructures feature a thick bar with 4 thin lines on the outer edge.
    Footprint: [120, 4]
    """
    c = gf.Component("gds_device_v4")
    
    # --- 1. Design Parameters ---
    WIDTH = 120.0
    TOTAL_HEIGHT = 4.0
    
    # Central Bus Params
    BUS_LINE_W = 0.08
    BUS_PITCH = 0.18
    
    # Superstructure Params
    THICK_W = 0.8
    THIN_W = 0.06
    THIN_SPACING = 0.12
    # Offsets for thin lines (we want them on the 'outside')
    # If we use a path with Right turns, 'Left' (positive) is Inner, 'Right' (negative) is Outer.
    super_offsets = [-0.6, -0.75, -0.9, -1.05] 
    
    # --- 2. Define Cross-Sections ---
    
    # Central Bus Cross-Section
    xs_bus = gf.cross_section.cross_section(
        sections=[
            gf.cross_section.Section(width=BUS_LINE_W, offset=(i - 2) * BUS_PITCH, layer=(1, 0))
            for i in range(5)
        ]
    )
    
    # Superstructure Cross-Section (1 thick + 4 thin)
    super_sections = [gf.cross_section.Section(width=THICK_W, offset=0, layer=(1, 0))]
    for offset in super_offsets:
        super_sections.append(gf.cross_section.Section(width=THIN_W, offset=offset, layer=(1, 0)))
    
    xs_super = gf.cross_section.cross_section(sections=super_sections)
    
    # --- 3. Construct Components ---
    
    # 3.1 Central Bus
    bus = c << gf.components.straight(length=WIDTH, cross_section=xs_bus)
    bus.x = 0
    bus.y = 0
    
    # 3.2 Top Superstructure
    # Strategy: Start top-right, go down, turn west, turn north. 
    # This creates a U with two Right turns (-90 deg). 
    # Negative offsets in the cross-section will appear on the 'Outside'.
    R = 2.0         # Bend radius
    EAR_H = 1.0     # Vertical length of the ear tips
    HORIZ_L = 110.0 # Length of the horizontal segment
    
    p_top = gf.Path()
    p_top.append(gf.path.straight(length=EAR_H).rotate(-90)) # Down from top-right
    p_top.append(gf.path.euler(radius=R, angle=-90))         # Turn Right (facing West)
    p_top.append(gf.path.straight(length=HORIZ_L))          # Horizontal span
    p_top.append(gf.path.euler(radius=R, angle=-90))         # Turn Right (facing North)
    p_top.append(gf.path.straight(length=EAR_H))            # Up at top-left
    
    top_comp = gf.path.extrude(p_top, cross_section=xs_super)
    top_ref = c << top_comp
    
    # Position Top: Center it and move it above the bus
    top_ref.x = 0
    top_ref.y = 0.8  # Adjust to create the visual gap
    
    # 3.3 Bottom Superstructure
    # Simply mirror the top one
    bottom_ref = c << top_comp
    bottom_ref.mirror_y()
    bottom_ref.x = 0
    bottom_ref.y = -0.8
    
    # --- 4. Final Alignment Check ---
    # The total width is defined by HORIZ_L + 2*R + (thin line offsets)
    # The total height is defined by (top_ref.y + EAR_H + R) * 2
    # These values (approx 116um x 3.6um) fit safely in [120, 4]
    
    return c

if __name__ == "__main__":
    component = device_geometry_turn4()
    component.write_gds("device_iteration_4.gds")
    component.show()