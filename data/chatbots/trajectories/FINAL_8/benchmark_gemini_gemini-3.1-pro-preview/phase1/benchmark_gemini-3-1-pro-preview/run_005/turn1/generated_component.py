import gdsfactory as gf

@gf.cell
def mode_converter_structure():
    c = gf.Component("main")
    
    # We will build all the tracks into a raw geometry component first, 
    # then use a boolean intersection to perfectly crop it to the 120x4 footprint limit.
    raw = gf.Component("raw_geom")
    
    # --- Dimensions & Layout Parameters ---
    L_total = 120.0
    L_straight = 60.0
    L_bend = (L_total - L_straight) / 2.0  # 30.0 um per flared bend
    
    w_thin = 0.06
    gap = 0.06
    w_thick_inner = 0.30
    w_thick_outer = 1.20
    dy_flare = 0.70  # The vertical distance the outer branches bend outwards
    
    # --- 1. Central Straight Tracks ---
    # 5 thin lines running straight down the center
    xs_thin = gf.cross_section.cross_section(width=w_thin, layer=(1, 0))
    for i in range(-2, 3):
        y = i * (w_thin + gap)
        st = gf.components.straight(length=L_total, cross_section=xs_thin)
        ref = raw << st
        ref.move((-L_total / 2.0, y))  # Center the straight segment on X=0

    # --- 2. Helper Function for Flared Branches ---
    def add_flare(comp, width, y_mid, dy):
        """Builds a symmetrical flared waveguide using standard straight and S-bend components."""
        xs = gf.cross_section.cross_section(width=width, layer=(1, 0))
        
        # Central straight part
        st = gf.components.straight(length=L_straight, cross_section=xs)
        st_ref = comp << st
        st_ref.move((-L_straight / 2.0, y_mid))
        
        # Left S-bend (connects o2 to straight's o1)
        # Supplying a negative dy creates a bend perfectly tailored to inverse upward curves.
        b_left = gf.components.bend_s(size=(L_bend, -dy), cross_section=xs)
        bl_ref = comp << b_left
        bl_ref.connect("o2", st_ref.ports["o1"])
        
        # Right S-bend (connects o1 to straight's o2)
        b_right = gf.components.bend_s(size=(L_bend, dy), cross_section=xs)
        br_ref = comp << b_right
        br_ref.connect("o1", st_ref.ports["o2"])

    # --- 3. Build Top and Bottom Flared Sections ---
    def build_symmetric_half(direction_mult):
        # Multiplier of 1 builds the top curving UP. Multiplier of -1 builds the bottom curving DOWN.
        y_inner = 0.48 * direction_mult
        dy = dy_flare * direction_mult
        
        # Inner thick flare
        add_flare(raw, w_thick_inner, y_inner, dy)
        
        # 4 intermediate thin flares
        y_thins = [0.72, 0.84, 0.96, 1.08]
        for y_val in y_thins:
            add_flare(raw, w_thin, y_val * direction_mult, dy)
            
        # Outer thick block (made intentionally oversized to get smoothly chopped by the bounding box later)
        y_outer = 1.77 * direction_mult
        add_flare(raw, w_thick_outer, y_outer, dy)

    # Top half (positive Y, curves UP)
    build_symmetric_half(1)
    
    # Bottom half (negative Y, curves DOWN)
    build_symmetric_half(-1)

    # --- 4. Enforce Footprint with Boolean Cropping ---
    # This intersects our entire geometry with a 120x4 rectangle.
    # It creates the perfectly flat cut top and bottom extremities visible on the device.
    bbox = gf.components.rectangle(size=(120.0, 4.0), layer=(1, 0), centered=True)
    final_geom = gf.boolean(A=raw, B=bbox, operation="and", layer=(1, 0))
    
    c << final_geom

    return c


if __name__ == "__main__":
    # Ensure the script triggers construction and produces the actual GDS file.
    c = mode_converter_structure()
    c.write_gds("device.gds")