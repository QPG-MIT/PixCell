import gdsfactory as gf

@gf.cell
def device_geometry_turn3():
    """
    Recreates the device with a central 5-line bus and two curved superstructures.
    The superstructures use 'ears' that curve away from the center.
    Footprint: [120, 4]
    """
    c = gf.Component("improved_device_v3")
    
    # --- 1. Define Design Parameters ---
    WIDTH = 120.0
    RADIUS = 12.0      # Large radius for gentle 'ear' curves
    EAR_HEIGHT = 2.0   # Vertical extent of the flares
    
    # --- 2. Define Cross-Sections ---
    
    # Central Bus: 5 parallel thin lines
    bus_sections = [
        gf.cross_section.Section(width=0.08, offset=(i - 2) * 0.18, layer=(1, 0))
        for i in range(5)
    ]
    xs_bus = gf.cross_section.cross_section(sections=bus_sections)
    
    # Superstructure Cross-Section (1 thick bar + 4 thin lines)
    # We use positive offsets here; we'll orient the path so these are 'outside'
    super_sections = [
        gf.cross_section.Section(width=0.8, offset=0.4, layer=(1, 0)),    # Thick inner bar
        gf.cross_section.Section(width=0.08, offset=1.0, layer=(1, 0)),  # Thin line 1
        gf.cross_section.Section(width=0.08, offset=1.2, layer=(1, 0)),  # Thin line 2
        gf.cross_section.Section(width=0.08, offset=1.4, layer=(1, 0)),  # Thin line 3
        gf.cross_section.Section(width=0.08, offset=1.6, layer=(1, 0)),  # Thin line 4
    ]
    xs_super = gf.cross_section.cross_section(sections=super_sections)
    
    # --- 3. Build Central Bus ---
    bus_path = gf.path.straight(length=WIDTH)
    bus = c << gf.path.extrude(bus_path, cross_section=xs_bus)
    bus.movex(-WIDTH / 2)
    
    # --- 4. Build Superstructures (Top and Bottom) ---
    
    # We create a 'cap' path for the top: 
    # Starts at right end (vertical down) -> curves left to horizontal -> curves left to vertical up
    # This ensures 'Left' (positive offset) is always the 'outside' of the shape.
    p_top = gf.Path()
    p_top.append(gf.path.straight(length=EAR_HEIGHT).rotate(180)) # Start at top-right, go down
    p_top.append(gf.path.euler(radius=RADIUS, angle=90))           # Turn left to go West
    p_top.append(gf.path.straight(length=WIDTH - 2 * RADIUS))     # Long horizontal span
    p_top.append(gf.path.euler(radius=RADIUS, angle=90))           # Turn left to go North
    p_top.append(gf.path.straight(length=EAR_HEIGHT))             # Finish vertical
    
    # Extrude the complex cross-section along this U-path
    super_comp = gf.path.extrude(p_top, cross_section=xs_super)
    
    # Add Top Superstructure
    # Position it so the horizontal segment is just above the bus
    top_ref = c << super_comp
    top_ref.movey(0.5) 
    top_ref.movex(WIDTH / 2) # Align centered horizontally
    
    # Add Bottom Superstructure (Mirror of Top)
    bottom_ref = c << super_comp
    bottom_ref.mirror_y()
    bottom_ref.movey(-0.5)
    bottom_ref.movex(WIDTH / 2)
    
    return c

if __name__ == "__main__":
    # Create the component
    component = device_geometry_turn3()
    
    # Export and visualize
    component.write_gds("device_iteration_3.gds")
    component.show()