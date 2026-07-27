import gdsfactory as gf

@gf.cell
def racetrack_mzi_device():
    """
    Recreates the device from the image within a 5.5um x 3um footprint.
    Uses a manual list of references to ensure compatibility with all GDSFactory backends.
    """
    # Create a temporary component to serve as the coordinate system
    c = gf.Component()
    
    # List to manually track references for the final boolean operation
    ref_list = []
    
    # =======================================================================
    # Parameters
    # =======================================================================
    layer_main = (1, 0)
    
    # Geometry Constraints
    width_total = 5.5
    height_total = 3.0
    ring_thickness = 0.55
    
    # Inner structure parameters
    arm_y_offset = 0.65       
    pad_width = 0.75          
    pad_height = 0.55         
    center_gap = 0.25         
    
    # Define cross section for consistent layering
    xs = gf.cross_section.cross_section(width=ring_thickness, layer=layer_main)
    
    # =======================================================================
    # 1. Outer Racetrack Ring (Path Extrusion)
    # =======================================================================
    r_outer = height_total / 2.0
    r_center = r_outer - (ring_thickness / 2.0)
    l_straight = width_total - height_total 
    
    p = gf.Path()
    p.append(gf.path.straight(length=l_straight))
    p.append(gf.path.arc(radius=r_center, angle=180))
    p.append(gf.path.straight(length=l_straight))
    p.append(gf.path.arc(radius=r_center, angle=180))
    
    ring = gf.path.extrude(p, cross_section=xs)
    
    ref_ring = c << ring
    ref_ring.center = (0, 0)
    ref_list.append(ref_ring) # Add to manual list

    # =======================================================================
    # 2. Inner Rectangular Pads
    # =======================================================================
    rect = gf.components.rectangle(
        size=(pad_width, pad_height), 
        layer=layer_main, 
        centered=True
    )
    
    x_pos = (center_gap/2) + (pad_width/2)
    y_pos = arm_y_offset
    
    # Positions: TopRight, TopLeft, BottomRight, BottomLeft
    positions = [
        (x_pos, y_pos),
        (-x_pos, y_pos),
        (x_pos, -y_pos),
        (-x_pos, -y_pos)
    ]
    
    for pos in positions:
        ref = c << rect
        ref.move(pos)
        ref_list.append(ref) # Add to manual list

    # =======================================================================
    # 3. Connecting Tapers
    # =======================================================================
    x_start_taper = x_pos + (pad_width/2)
    x_ring_inner_est = (width_total/2) - ring_thickness
    taper_length = (x_ring_inner_est - x_start_taper) + 0.2 # Overlap for clean merge
    
    taper_w1 = pad_height
    taper_w2 = pad_height * 1.5 
    
    taper = gf.components.taper(
        length=taper_length, 
        width1=taper_w1, 
        width2=taper_w2,
        cross_section=xs
    )
    
    # Right side tapers
    t_tr = c << taper
    t_tr.move((x_start_taper, y_pos))
    ref_list.append(t_tr)
    
    t_br = c << taper
    t_br.move((x_start_taper, -y_pos))
    ref_list.append(t_br)
    
    # Left side tapers (Mirrored)
    t_tl = c << taper
    t_tl.mirror()
    t_tl.move((-x_start_taper, y_pos))
    ref_list.append(t_tl)
    
    t_bl = c << taper
    t_bl.mirror()
    t_bl.move((-x_start_taper, -y_pos))
    ref_list.append(t_bl)

    # =======================================================================
    # 4. Final Boolean Merge
    # =======================================================================
    # We pass 'ref_list' to both A and B. A union A = A.
    # This creates a single flat component on 'layer_main'
    merged_component = gf.boolean(A=ref_list, B=ref_list, operation="or", layer=layer_main)
    merged_component.name = "racetrack_mzi_device"
    
    return merged_component

if __name__ == "__main__":
    device = racetrack_mzi_device()
    device.show() 
    device.write_gds("racetrack_mzi.gds")
    
    # Verify dimensions
    print(f"Device created: {device.name}")
    print(f"Device bounds: {device.bbox}")