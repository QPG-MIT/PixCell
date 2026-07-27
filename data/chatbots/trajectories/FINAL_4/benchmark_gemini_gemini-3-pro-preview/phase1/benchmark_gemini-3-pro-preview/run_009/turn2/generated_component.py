import gdsfactory as gf

@gf.cell
def adiabatic_coupler_tight():
    """
    Creates an adiabatic directional coupler with a tight coupling gap.
    Footprint: 18um x 3um.
    """
    c = gf.Component()

    # --- Constraints & Parameters ---
    # Total Footprint dimensions
    length = 18.0
    total_height = 3.0
    
    # Split length for two bend stages (converge then diverge)
    x_step = length / 2

    # Visual adjustments based on the target image:
    # 1. Thicker waveguides to match the ink-to-white ratio.
    wg_width = 1.0 
    
    # 2. Much tighter gap at the waist. 
    # Previous was ~0.3um, target looks like ~0.14um.
    min_gap = 0.14

    # --- Geometry Calculations ---
    # The device bounds are y = -1.5 to y = 1.5 to fit height=3.0
    y_top_limit = total_height / 2
    y_bot_limit = -total_height / 2

    # 1. Calculate Start (Input) Y positions
    # Center y is positioned so the outer edge touches the limit.
    # Center = Limit - (Width / 2)
    y_start_top = y_top_limit - (wg_width / 2)  # 1.5 - 0.5 = 1.0
    y_start_bot = y_bot_limit + (wg_width / 2)  # -1.5 + 0.5 = -1.0

    # 2. Calculate Waist (Center) Y positions
    # Centers are separated by (Width + Gap)
    # Top Waist Y = (Width + Gap) / 2
    center_separation = wg_width + min_gap
    y_waist_top = center_separation / 2         # (1.0 + 0.14)/2 = 0.57
    y_waist_bot = -center_separation / 2        # -0.57

    # 3. Calculate Vertical Shift (dy) for the S-bends
    # How much does the waveguide drop from input to waist?
    dy = y_start_top - y_waist_top              # 1.0 - 0.57 = 0.43

    # Define Cross Section
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))

    # --- Construct Top Arm ---
    # Part 1: Converge (Input -> Waist) - Bends DOWN
    tl = c << gf.components.bend_s(size=(x_step, -dy), cross_section=xs)
    tl.move((-x_step, y_start_top))
    
    # Part 2: Diverge (Waist -> Output) - Bends UP
    tr = c << gf.components.bend_s(size=(x_step, dy), cross_section=xs)
    tr.connect("o1", tl.ports["o2"])

    # --- Construct Bottom Arm ---
    # Part 1: Converge (Input -> Waist) - Bends UP
    bl = c << gf.components.bend_s(size=(x_step, dy), cross_section=xs)
    bl.move((-x_step, y_start_bot))
    
    # Part 2: Diverge (Waist -> Output) - Bends DOWN
    br = c << gf.components.bend_s(size=(x_step, -dy), cross_section=xs)
    br.connect("o1", bl.ports["o2"])

    # --- Ports ---
    c.add_port("o1", port=tl.ports["o1"])
    c.add_port("o2", port=bl.ports["o1"])
    c.add_port("o3", port=tr.ports["o2"])
    c.add_port("o4", port=br.ports["o2"])

    return c

# Generate and save
device = adiabatic_coupler_tight()
device.write_gds("adiabatic_coupler_tight.gds")
device.show()