import gdsfactory as gf

@gf.cell
def adiabatic_coupler_tight():
    """
    Creates an adiabatic directional coupler with a tight coupling gap.
    Footprint: 18um x 3um.
    """
    c = gf.Component()

    # --- Constraints & Parameters ---
    length = 18.0
    total_height = 3.0
    
    # Adjusted parameters for better visual match:
    # Reduced wg_width to make waveguides thinner relative to the gap.
    # Increased min_gap to ensure the waist separation is clearly visible.
    wg_width = 0.65
    min_gap = 0.2

    # Define Cross Section
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))

    # --- Geometry Calculations ---
    x_step = length / 2

    # 1. Calculate Start (Input) Y positions
    # Position waveguides so outer edges align with the +/- 1.5um footprint limits.
    y_top_limit = total_height / 2
    y_start_top = y_top_limit - (wg_width / 2)
    y_start_bot = -y_start_top

    # 2. Calculate Waist (Center) Y positions
    # Waveguides are separated by min_gap at the center.
    y_waist_top = (wg_width + min_gap) / 2
    y_waist_bot = -y_waist_top

    # 3. Calculate Vertical Shift (dy) for the S-bends
    # dy is the vertical distance from start to waist
    dy_top = y_waist_top - y_start_top  # Negative value (moving down)
    dy_bot = y_waist_bot - y_start_bot  # Positive value (moving up)

    # --- Construct Top Arm ---
    # Part 1: Converge (Input -> Waist)
    tl = c << gf.components.bend_s(size=(x_step, dy_top), cross_section=xs)
    tl.move((-x_step, y_start_top))
    
    # Part 2: Diverge (Waist -> Output)
    # Mirror the vertical displacement for the output section
    tr = c << gf.components.bend_s(size=(x_step, -dy_top), cross_section=xs)
    tr.connect("o1", tl.ports["o2"])

    # --- Construct Bottom Arm ---
    # Part 1: Converge (Input -> Waist)
    bl = c << gf.components.bend_s(size=(x_step, dy_bot), cross_section=xs)
    bl.move((-x_step, y_start_bot))
    
    # Part 2: Diverge (Waist -> Output)
    br = c << gf.components.bend_s(size=(x_step, -dy_bot), cross_section=xs)
    br.connect("o1", bl.ports["o2"])

    # --- Ports ---
    c.add_port("o1", port=tl.ports["o1"])
    c.add_port("o2", port=bl.ports["o1"])
    c.add_port("o3", port=tr.ports["o2"])
    c.add_port("o4", port=br.ports["o2"])

    return c

if __name__ == "__main__":
    device = adiabatic_coupler_tight()
    device.write_gds("adiabatic_coupler_tight.gds")
    device.show()