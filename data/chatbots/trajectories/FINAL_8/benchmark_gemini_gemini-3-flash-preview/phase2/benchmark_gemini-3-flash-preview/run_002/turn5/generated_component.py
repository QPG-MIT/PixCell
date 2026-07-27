import gdsfactory as gf

@gf.cell
def recreate_final_geometry_v5():
    """
    Turn 5: Accurate recreation of the device geometry.
    - Prominent double-line side rails with outward Euler flares.
    - Precisely balanced vertical spacing to fit the 4.0 um footprint.
    - Central lines extend further horizontally than the wing components.
    """
    c = gf.Component("device_iteration_5")
    layer = (1, 0)
    
    # --- 1. Parameters ---
    WIDTH_TOTAL = 120.0
    WIDTH_WING = 100.0
    # Vertical budget: +/- 2.0 um from center
    
    # --- 2. Central Horizontal Section (5 lines) ---
    # Centered at y=0, taking up ~0.4um height
    mid_w = 0.04
    mid_pitch = 0.1
    for i in range(5):
        line = c << gf.components.rectangle(size=(WIDTH_TOTAL, mid_w), layer=layer, centered=True)
        line.movey((i - 2) * mid_pitch)

    # --- 3. Wing Structure Generator ---
    def make_wing():
        wing = gf.Component()
        
        # A. Thick Horizontal Base Bar
        # This is the main "body" of the wing
        bar_h = 0.7
        bar = gf.components.rectangle(size=(WIDTH_WING, bar_h), layer=layer, centered=True)
        # Position so the inner edge is ~0.6um from the center
        b_ref = wing << bar
        b_ref.movey(0.6 + bar_h/2) # Bounds: y=0.6 to y=1.3
        
        # B. 4 Thin Horizontal Ribs
        # Placed on the outer side of the thick bar
        rib_w = 0.04
        rib_pitch = 0.14
        rib_start_y = 1.45
        for i in range(4):
            r_ref = wing << gf.components.rectangle(size=(WIDTH_WING, rib_w), layer=layer, centered=True)
            r_ref.movey(rib_start_y + i * rib_pitch) # Bounds: ~1.45 to ~1.9
            
        # C. Double Flared Side Rails (The "Horns")
        # These bound the wing horizontally and flare outward
        rail_w = 0.08
        rail_gap = 0.12
        
        # Define a path that starts vertical and then flares out using an Euler spiral
        # Total height of the rail is roughly 1.4um (from y=0.6 to y=2.0)
        rail_path = gf.path.straight(length=0.7) + gf.path.euler(radius=2.0, angle=25)
        
        # Create a double-line cross section for the rail
        xs = gf.CrossSection(
            sections=[
                gf.Section(width=rail_w, offset=0, layer=layer),
                gf.Section(width=rail_w, offset=-(rail_w + rail_gap), layer=layer)
            ]
        )
        rail_comp = gf.path.extrude(rail_path, cross_section=xs)
        
        # Place Left Rail (Flares to the Left)
        l_rail = wing << rail_comp
        l_rail.rotate(90) # Rotate to point upward
        # After rotation, path bends left naturally. 
        l_rail.movex(-WIDTH_WING/2).movey(0.6)
        
        # Place Right Rail (Flares to the Right)
        r_rail = wing << rail_comp
        r_rail.rotate(90)
        r_rail.mirror(p1=(0,0), p2=(0,1)) # Mirror across Y-axis to flare right
        r_rail.movex(WIDTH_WING/2).movey(0.6)
        
        return wing

    # --- 4. Assembly and Vertical Symmetry ---
    # Add Top Wing
    top_wing = c << make_wing()
    
    # Add Bottom Wing (Mirrored copy of top)
    bot_wing = c << make_wing()
    bot_wing.mirror(p1=(0, 0), p2=(1, 0)) # Mirror across X-axis

    return c

if __name__ == "__main__":
    # Generate the component
    device = recreate_final_geometry_v5()
    
    # Export to GDS for fabrication/inspection
    output_filename = "device_iteration_5.gds"
    device.write_gds(output_filename)
    
    print(f"Successfully generated: {output_filename}")
    # device.show() # Uncomment to view in KLayout