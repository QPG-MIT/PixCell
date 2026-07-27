import gdsfactory as gf

@gf.cell
def recreate_final_geometry():
    """
    Recreates the device geometry with flared vertical rails.
    Footprint: 120.0 um x 4.0 um.
    """
    c = gf.Component("final_device")
    layer = (1, 0)
    
    # --- 1. Central Horizontal Lines (120um wide) ---
    # 5 thin lines centered at y=0
    mid_w = 0.08
    mid_pitch = 0.16
    mid_rect = gf.components.rectangle(size=(120, mid_w), layer=layer, centered=True)
    for i in range(5):
        # We move the REFERENCE, not the component, to avoid the locking error
        ref = c << mid_rect
        ref.movey((i - 2) * mid_pitch)

    # --- 2. Define the "Wing" Component (Top structure) ---
    def make_wing():
        wing = gf.Component()
        
        # A. Horizontal Ribs
        # One thick base bar and 4 thin ribs
        thick_bar = gf.components.rectangle(size=(100, 0.6), layer=layer, centered=True)
        t_ref = wing << thick_bar
        t_ref.movey(0.7) # Positioned above the center gap
        
        thin_rib = gf.components.rectangle(size=(100, 0.08), layer=layer, centered=True)
        for i in range(4):
            r_ref = wing << thin_rib
            r_ref.movey(1.2 + i * 0.22)
            
        # B. Vertical Rails (The "Container" effect)
        # Inner straight rails at the ends of the 100um horizontal lines
        rail_w = 0.1
        inner_rail_comp = gf.components.rectangle(size=(rail_w, 1.4), layer=layer, centered=True)
        (wing << inner_rail_comp).movex(-50).movey(1.3)
        (wing << inner_rail_comp).movex(50).movey(1.3)
        
        # C. Outer Flared Rails using Paths
        # Create a path that goes straight and then curves outward
        # Using gf.path.euler for the smooth "horn" look
        rail_path = gf.path.straight(length=1.3) + gf.path.euler(radius=1.5, angle=35)
        rail_xs = gf.cross_section.cross_section(width=rail_w, layer=layer)
        flared_rail_comp = gf.path.extrude(rail_path, cross_section=rail_xs)
        
        # Place Left Flared Rail (Mirror to curve left)
        l_flare = wing << flared_rail_comp
        l_flare.rotate(90).mirror().movex(-52).movey(0.6)
        
        # Place Right Flared Rail (Curve right)
        r_flare = wing << flared_rail_comp
        r_flare.rotate(90).movex(52).movey(0.6)
        
        return wing

    # --- 3. Assemble and Mirror ---
    wing_component = make_wing()
    
    # Top Wing
    c << wing_component
    
    # Bottom Wing (Mirrored Reference)
    bottom_wing = c << wing_component
    bottom_wing.mirror(p1=(0, 0), p2=(1, 0)) # Flip across X-axis

    return c

if __name__ == "__main__":
    # Build component
    device = recreate_final_geometry()
    
    # Write to GDS
    output_filename = "device_recreation.gds"
    device.write_gds(output_filename)
    
    print(f"Successfully generated: {output_filename}")
    # device.show() # Uncomment to view in KLayout