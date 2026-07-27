import gdsfactory as gf

@gf.cell
def recreate_final_geometry():
    c = gf.Component("refined_device")
    layer = (1, 0)
    
    # Device dimensions from footprint: 120um x 4um
    total_w = 120.0
    total_h = 4.0
    
    # 1. CENTRAL GRATING (The 5 longest lines)
    # These span the full width of the device
    h_thin = 0.06
    spacing = 0.12
    central_line = gf.components.rectangle(size=(total_w, h_thin), layer=layer, centered=True)
    
    for i in range(5):
        y_offset = (i - 2) * spacing
        ref = c << central_line
        ref.movey(y_offset)

    # 2. SIDE FLARED WALLS (The "Brackets")
    # We use a Path to create the inward-curving vertical walls
    # Right-side top quadrant path
    wall_pts = [(48.0, 0.45), (49.0, 1.2), (54.0, 2.0)]
    path_quadrant = gf.Path(wall_pts)
    wall_section = gf.path.extrude(path_quadrant, width=1.5, layer=layer)
    
    # Place all four mirrored quadrants by transforming references
    # Top-Right
    c << wall_section
    # Bottom-Right
    ref_br = c << wall_section
    ref_br.mirror_y()
    # Top-Left
    ref_tl = c << wall_section
    ref_tl.mirror_x()
    # Bottom-Left
    ref_bl = c << wall_section
    ref_bl.mirror_x()
    ref_bl.mirror_y()

    # 3. INTERNAL BODY STRUCTURES (Thick bars and outer fins)
    # These are shorter than the central grating, sitting between the side walls
    inner_w = 95.0
    h_thick = 0.75
    
    # Create templates
    thick_bar = gf.components.rectangle(size=(inner_w, h_thick), layer=layer, centered=True)
    outer_thin_line = gf.components.rectangle(size=(inner_w, h_thin), layer=layer, centered=True)
    
    # Top Body
    ref_thick_t = c << thick_bar
    ref_thick_t.movey(1.05)
    for i in range(4):
        ref_thin_t = c << outer_thin_line
        ref_thin_t.movey(1.55 + i * spacing)
        
    # Bottom Body (Mirrored)
    ref_thick_b = c << thick_bar
    ref_thick_b.movey(-1.05)
    for i in range(4):
        ref_thin_b = c << outer_thin_line
        ref_thin_b.movey(-(1.55 + i * spacing))

    return c

if __name__ == "__main__":
    # Generate the component
    device = recreate_final_geometry()
    
    # Show in KLayout or GDS viewer
    device.show()
    
    # Save the GDS
    device.write_gds("recreated_geometry_v2.gds")