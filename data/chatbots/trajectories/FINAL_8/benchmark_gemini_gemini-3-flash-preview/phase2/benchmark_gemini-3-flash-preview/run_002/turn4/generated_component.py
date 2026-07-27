import gdsfactory as gf

@gf.cell
def recreate_final_geometry_v4():
    """
    Recreates the device geometry with improved vertical proportions and 
    prominent double-flared side rails.
    Target Footprint: 120.0 um x 4.0 um.
    """
    c = gf.Component("device_iteration_4")
    layer = (1, 0)
    
    # --- 1. Parameters ---
    total_width = 120.0
    wing_width = 100.0  # Width of the horizontal ribs
    rail_x_pos = wing_width / 2
    
    # --- 2. Central Horizontal Lines (5 lines) ---
    # Centered at y=0, taking up ~0.6um height
    mid_w = 0.06
    mid_pitch = 0.12
    mid_rect = gf.components.rectangle(size=(total_width, mid_w), layer=layer, centered=True)
    for i in range(5):
        ref = c << mid_rect
        ref.movey((i - 2) * mid_pitch)

    # --- 3. The "Wing" Component (Top structure) ---
    def make_wing():
        wing = gf.Component()
        
        # A. Thick Base Bar
        thick_h = 0.6
        thick_bar = gf.components.rectangle(size=(wing_width, thick_h), layer=layer, centered=True)
        t_ref = wing << thick_bar
        t_ref.movey(0.8) # Positioned above the central gap
        
        # B. 4 Thin Horizontal Ribs
        rib_w = 0.06
        rib_pitch = 0.18
        thin_rib = gf.components.rectangle(size=(wing_width, rib_w), layer=layer, centered=True)
        for i in range(4):
            r_ref = wing << thin_rib
            r_ref.movey(1.3 + i * rib_pitch)
            
        # C. Double Flared Rails (The "Horns")
        # Creating a cross-section with two lines to ensure perfect parallel routing
        rail_w = 0.06
        rail_gap = 0.3
        
        # Define a path that starts vertical and then flares out
        # Length is roughly the height of the wing components (~1.2um)
        rail_path = gf.path.straight(length=1.0) + gf.path.euler(radius=4.0, angle=25)
        
        # Create a double-line cross section
        xs = gf.CrossSection(
            sections=[
                gf.Section(width=rail_w, offset=0, layer=layer),
                gf.Section(width=rail_w, offset=rail_gap, layer=layer)
            ]
        )
        rail_comp = gf.path.extrude(rail_path, cross_section=xs)
        
        # Place rails on Left and Right
        for side in [-1, 1]:
            ref = wing << rail_comp
            ref.rotate(90)
            if side == -1:
                ref.mirror() # Flip for the left side
            
            # Anchor the start of the rail to the base of the thick bar
            ref.movex(side * rail_x_pos).movey(0.5)
        
        return wing

    # --- 4. Assembly and Vertical Mirroring ---
    top_wing = c << make_wing()
    
    # Mirror the top wing to create the bottom half
    bottom_wing = c << make_wing()
    bottom_wing.mirror(p1=(0, 0), p2=(1, 0))

    return c

if __name__ == "__main__":
    # Create the component
    device = recreate_final_geometry_v4()
    
    # Export to GDS
    output_filename = "device_iteration_4.gds"
    device.write_gds(output_filename)
    
    print(f"Successfully generated: {output_filename}")
    # device.show() # Uncomment to view in KLayout