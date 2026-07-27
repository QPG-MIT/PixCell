import gdsfactory as gf

@gf.cell
def recreate_final_geometry():
    """
    Recreates the device geometry with a focus on the double-flared side rails 
     and correct vertical proportions.
    Footprint target: 120.0 um x 4.0 um.
    """
    c = gf.Component("final_device_v3")
    layer = (1, 0)
    
    # --- 1. Central Horizontal Lines (120um wide) ---
    # 5 thin lines centered at y=0. Total span ~0.8um
    mid_w = 0.08
    mid_pitch = 0.16
    mid_rect = gf.components.rectangle(size=(120, mid_w), layer=layer, centered=True)
    for i in range(5):
        ref = c << mid_rect
        ref.movey((i - 2) * mid_pitch)

    # --- 2. Define the "Wing" Component (Top structure) ---
    def make_wing():
        wing = gf.Component()
        wing_w = 100
        
        # A. Horizontal Ribs
        # One thick base bar and 4 thin ribs above it
        thick_h = 0.5
        thick_bar = gf.components.rectangle(size=(wing_w, thick_h), layer=layer, centered=True)
        t_ref = wing << thick_bar
        t_ref.movey(0.9) # Positioned above the center gap
        
        rib_w = 0.08
        rib_pitch = 0.22
        thin_rib = gf.components.rectangle(size=(wing_w, rib_w), layer=layer, centered=True)
        for i in range(4):
            r_ref = wing << thin_rib
            r_ref.movey(1.35 + i * rib_pitch)
            
        # B. Double Flared Rails (The "Horns")
        # We create a path that starts vertical and then curves outward
        rail_w = 0.08
        rail_gap = 0.25 # Spacing between the double rails
        
        # Path: straight segment next to the thick bar, then a smooth euler flare
        rail_path = gf.path.straight(length=0.6) + gf.path.euler(radius=3.0, angle=25)
        rail_xs = gf.cross_section.cross_section(width=rail_w, layer=layer)
        rail_comp = gf.path.extrude(rail_path, cross_section=rail_xs)
        
        # Helper to place rails symmetrically
        for side in [-1, 1]: # -1 for Left, 1 for Right
            # Inner Rail
            inner = wing << rail_comp
            inner.rotate(90)
            if side == -1: inner.mirror()
            inner.movex(side * (wing_w / 2)).movey(0.65)
            
            # Outer Rail
            outer = wing << rail_comp
            outer.rotate(90)
            if side == -1: outer.mirror()
            outer.movex(side * (wing_w / 2 + rail_gap)).movey(0.65)
        
        return wing

    # --- 3. Assemble and Mirror ---
    wing_component = make_wing()
    
    # Top Wing
    c << wing_component
    
    # Bottom Wing (Mirrored Reference)
    bottom_wing = c << wing_component
    bottom_wing.mirror(p1=(0, 0), p2=(1, 0)) # Flip across X-axis to create the bottom half

    return c

if __name__ == "__main__":
    # Create the component
    device = recreate_final_geometry()
    
    # Export to GDS
    output_filename = "device_iteration_3.gds"
    device.write_gds(output_filename)
    
    print(f"Successfully generated: {output_filename}")
    # To view the result, use a GDS viewer like KLayout:
    # device.show()