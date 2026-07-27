import gdsfactory as gf

@gf.cell
def routing_slot(width: float = 0.08, length: float = 122.0, L_straight: float = 50.0, dy: float = 0.6) -> gf.Component:
    """
    Creates a single parametric slot path. 
    By making it slightly longer than the footprint (122 vs 120), we ensure 
    clean boolean cuts at the left and right boundaries without edge artifacts.
    """
    c = gf.Component()
    xs = gf.cross_section.cross_section(width=width, layer=(1, 0))

    # If it's a perfectly straight middle slot
    if abs(dy) < 1e-6:
        s = c << gf.components.straight(length=length, cross_section=xs)
        s.move((-length/2, 0))
        return c

    # If it's a curved outer slot
    L_sbend = (length - L_straight) / 2.0
    
    # Left S-bend
    b1 = c << gf.components.bend_s(size=(L_sbend, -dy), cross_section=xs)
    b1.move((-L_sbend - L_straight/2, dy))
    
    # Center straight section
    s1 = c << gf.components.straight(length=L_straight, cross_section=xs)
    s1.move((-L_straight/2, 0))
    
    # Right S-bend
    b2 = c << gf.components.bend_s(size=(L_sbend, dy), cross_section=xs)
    b2.move((L_straight/2, 0))
    
    return c

@gf.cell
def recreating_geometry() -> gf.Component:
    """
    Recreates the exact geometry utilizing a subtractive (trench) methodology. 
    A solid bounding rectangle has perfectly pitched slots subtracted from it, 
    naturally forming the required wedges and straight/curved trace layouts.
    """
    c = gf.Component("parallel_slot_coupler_subtractive")
    
    # --- Base Geometric Parameters ---
    length = 120.0
    height = 4.0
    
    pitch = 0.16         # Center-to-center distance between adjacent slots
    w_slot = 0.08        # Uniform thickness of the empty slots
    dy_shift = 0.7       # Vertical deviation of the curved slots at the ends
    L_str = 50.0         # Length of the middle flat coupling section
    
    slots_comp = gf.Component("all_slots")
    
    # --- 1. Bottom Curved Slots (4 slots) ---
    # These create the 3 thin lines at the bottom edges and shape the lower wedge
    for i in [-6.5, -5.5, -4.5, -3.5]:
        ref = slots_comp << routing_slot(width=w_slot, L_straight=L_str, dy=-dy_shift)
        ref.move((0, i * pitch))
        
    # --- 2. Middle Straight Slots (6 slots) ---
    # 6 straight slots precisely carve out the 5 perfectly straight thin lines in the middle
    for i in [-2.5, -1.5, -0.5, 0.5, 1.5, 2.5]:
        ref = slots_comp << routing_slot(width=w_slot, L_straight=L_str, dy=0.0)
        ref.move((0, i * pitch))
        
    # --- 3. Top Curved Slots (4 slots) ---
    # These create the 3 thin lines at the top edges and shape the upper wedge
    for i in [3.5, 4.5, 5.5, 6.5]:
        ref = slots_comp << routing_slot(width=w_slot, L_straight=L_str, dy=dy_shift)
        ref.move((0, i * pitch))
        
    # --- 4. Subtractive Operation ---
    # Base solid canvas
    rect = gf.components.rectangle(size=(length, height), centered=True, layer=(1, 0))
    
    # Subtracting the slots from the canvas yields the target complex masks
    final_c = gf.boolean(A=rect, B=slots_comp, operation="not", layer=(1, 0))
    
    return final_c

if __name__ == "__main__":
    device = recreating_geometry()
    device.write_gds("output.gds")