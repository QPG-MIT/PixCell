import gdsfactory as gf
import numpy as np

# Helper to ensure grid snapping (1nm grid)
def snap(val):
    return np.round(val, 3)

def get_s_bend_points(length, height, n=101):
    """
    Generates (x, y) points for a smooth cosine S-bend path.
    Includes explicit flat segments at start and end to enforce 0-degree ports,
    preventing off-grid rotation errors.
    """
    # Grid step for the flat guard sections (1nm)
    grid = 0.001
    
    # Generate full cosine curve points
    x_full = np.linspace(0, length, n)
    # Cosine S-bend formula: y(x) = (h/2) * (1 - cos(pi * x / L))
    y_full = (height / 2) * (1 - np.cos(np.pi * x_full / length))
    
    points = np.column_stack((x_full, y_full))
    
    # --- Tangent Guards ---
    # Force the first 2 points to be perfectly horizontal
    points[0] = [0, 0]
    points[1] = [grid, 0] 
    
    # Force the last 2 points to be perfectly horizontal
    points[-1] = [length, height]
    points[-2] = [length - grid, height] 
    
    # Snap all points to 1nm grid to satisfy foundry constraints
    points = np.round(points, 3)
    
    return points

@gf.cell
def adiabatic_coupler_4x240():
    """
    Adiabatic Directional Coupler (4x240um).
    Uses robust path generation to ensure on-grid placement.
    """
    c = gf.Component()

    # --- 1. Dimensions ---
    total_length = 240.0
    len_taper = 80.0
    len_flat = 80.0 # 240 - 80 - 80
    
    # Vertical Layout
    y_input_top = 1.5 
    
    # Coupling Region Layout
    gap = 0.2
    w_narrow = 0.5
    w_wide = 1.0
    
    # Center Y of the top waveguide in coupling region
    y_couple_top = (gap + w_narrow) / 2 # 0.35
    
    # Height change for Input Taper (moves Down)
    dy_in = snap(y_couple_top - y_input_top) # -1.15

    # --- 2. Cross Sections & Transitions ---
    xs_wide = gf.cross_section.cross_section(width=w_wide, layer=(1, 0))
    xs_narrow = gf.cross_section.cross_section(width=w_narrow, layer=(1, 0))
    
    # Width transitions
    trans_in = gf.path.transition(xs_wide, xs_narrow, width_type='sine')
    trans_out = gf.path.transition(xs_narrow, xs_wide, width_type='sine')

    # --- 3. Path Generation ---
    # Input Path: Wide -> Narrow, moves DOWN by dy_in
    points_in = get_s_bend_points(len_taper, dy_in)
    path_in = gf.Path(points_in)
    
    # Output Path: Narrow -> Wide, moves UP by -dy_in (return to original height)
    points_out = get_s_bend_points(len_taper, -dy_in)
    path_out = gf.Path(points_out)

    # --- 4. Assembly ---
    
    # -- Top Arm --
    # 4a. Input Taper
    taper_in = c << gf.path.extrude_transition(path_in, trans_in)
    taper_in.move((0, y_input_top))
    
    # 4b. Coupling Region
    # Connects to 'o2' of taper. Taper 'o2' is now guaranteed 0 degrees orientation.
    couple_straight = c << gf.components.straight(length=len_flat, cross_section=xs_narrow)
    couple_straight.connect("o1", taper_in.ports["o2"])
    
    # 4c. Output Taper
    taper_out = c << gf.path.extrude_transition(path_out, trans_out)
    taper_out.connect("o1", couple_straight.ports["o2"])
    
    # -- Bottom Arm (Mirrored) --
    # 4d. Bottom Input
    bot_taper_in = c << gf.path.extrude_transition(path_in, trans_in)
    bot_taper_in.mirror(p1=(0,0), p2=(1,0)) # Mirror vertically
    bot_taper_in.move((0, -y_input_top))
    
    # 4e. Bottom Coupling Region
    bot_couple = c << gf.components.straight(length=len_flat, cross_section=xs_narrow)
    bot_couple.connect("o1", bot_taper_in.ports["o2"])
    
    # 4f. Bottom Output
    bot_taper_out = c << gf.path.extrude_transition(path_out, trans_out)
    bot_taper_out.mirror(p1=(0,0), p2=(1,0)) # Mirror vertically
    bot_taper_out.connect("o1", bot_couple.ports["o2"])

    # --- 5. Ports ---
    c.add_port("o1", port=taper_in.ports["o1"])
    c.add_port("o2", port=bot_taper_in.ports["o1"])
    c.add_port("o3", port=taper_out.ports["o2"])
    c.add_port("o4", port=bot_taper_out.ports["o2"])

    return c

if __name__ == "__main__":
    device = adiabatic_coupler_4x240()
    device.write_gds("adiabatic_coupler.gds")
    device.show()