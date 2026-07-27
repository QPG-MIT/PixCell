import gdsfactory as gf

@gf.cell
def improved_device_geometry():
    """
    Recreates the device using multi-lane cross-sections and path extrusion.
    This creates the curved 'ears' seen in the original image.
    Footprint: [120, 4]
    """
    c = gf.Component("improved_device")
    
    # --- 1. Define Cross-Sections ---
    
    # Central Bus: 5 parallel thin lines
    bus_sections = [
        gf.cross_section.Section(width=0.12, offset=(i-2)*0.25, layer=(1, 0))
        for i in range(5)
    ]
    xs_bus = gf.cross_section.cross_section(sections=bus_sections)
    
    # Superstructure: 1 thick bar + 4 thin lines
    # These offsets are relative to the extrusion path
    super_sections = [
        gf.cross_section.Section(width=0.6, offset=0.2, layer=(1, 0)),   # Thick horizontal block
        gf.cross_section.Section(width=0.08, offset=0.65, layer=(1, 0)), # Thin line 1
        gf.cross_section.Section(width=0.08, offset=0.85, layer=(1, 0)), # Thin line 2
        gf.cross_section.Section(width=0.08, offset=1.05, layer=(1, 0)), # Thin line 3
        gf.cross_section.Section(width=0.08, offset=1.25, layer=(1, 0)), # Thin line 4
    ]
    xs_super = gf.cross_section.cross_section(sections=super_sections)
    
    # --- 2. Build Central Bus ---
    
    # Straight path spanning the full 120um width
    bus_path = gf.path.straight(length=120)
    bus = c << gf.path.extrude(bus_path, cross_section=xs_bus)
    bus.movex(-60) # Center the 120um bus at x=0
    
    # --- 3. Build Superstructures (Top and Bottom) ---
    
    # We create a 'tray' path: Vertical -> 90 deg Euler Bend -> Straight -> 90 deg Euler Bend -> Vertical
    # This ensures the 'ears' are perfectly curved as per the image.
    radius = 2.5
    h_ear = 0.6  # Height of the vertical part of the flare
    
    p_super = gf.Path()
    p_super.append(gf.path.straight(length=h_ear))      # Start vertical
    p_super.append(gf.path.euler(radius=radius, angle=-90)) # Curve to horizontal
    p_super.append(gf.path.straight(length=120 - 2*radius)) # Main horizontal span
    p_super.append(gf.path.euler(radius=radius, angle=-90)) # Curve back to vertical
    p_super.append(gf.path.straight(length=h_ear))      # End vertical
    
    # Create the assembly by extruding the complex cross-section along the U-path
    superstructure = gf.path.extrude(p_super, cross_section=xs_super)
    
    # Add Top Superstructure
    top_ref = c << superstructure
    top_ref.rotate(90) # Rotate to align horizontal part with X-axis
    top_ref.movex(-60 + radius) # Align ends with the 120um footprint
    top_ref.movey(0.65) # Offset from the center bus
    
    # Add Bottom Superstructure (Mirror of Top)
    bottom_ref = c << superstructure
    bottom_ref.rotate(90)
    bottom_ref.mirror_y()
    bottom_ref.movex(-60 + radius)
    bottom_ref.movey(-0.65)
    
    return c

if __name__ == "__main__":
    component = improved_device_geometry()
    component.write_gds("improved_device.gds")
    component.show()