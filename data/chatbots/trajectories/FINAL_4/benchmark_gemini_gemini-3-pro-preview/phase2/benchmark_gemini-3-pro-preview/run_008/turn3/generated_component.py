import gdsfactory as gf

@gf.cell
def adiabatic_coupler():
    c = gf.Component()
    
    # 1. Dimensions & Constraints
    # The device footprint is constrained to 18um x 3um.
    total_length = 18.0
    total_height = 3.0
    
    # Visual analysis adjustments:
    # - The target image shows waveguides that are thinner relative to the input gap.
    # - The previous width (1.0um) resulted in a "heavy" look with a minimal gap.
    # - Reducing width to 0.8um and increasing gap to 0.3um creates the correct visual balance
    #   and ensures the central gap is distinct (white space visible), matching the target.
    wg_width = 0.8
    min_gap = 0.3
    
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))

    # 2. Geometric Calculations
    # Split the length into converging (input -> waist) and diverging (waist -> output) halves.
    half_length = total_length / 2.0
    
    # Calculate Y positions relative to the center line (y=0)
    
    # Start Position: Waveguides are flush with the vertical boundaries of the 3um footprint.
    # Top WG Center Y = (Total Height / 2) - (Waveguide Width / 2)
    y_top_start = (total_height / 2.0) - (wg_width / 2.0)
    
    # Waist Position: Waveguides are separated by the minimum gap.
    # Top WG Center Y = (Gap / 2) + (Waveguide Width / 2)
    y_top_waist = (min_gap / 2.0) + (wg_width / 2.0)
    
    # Calculate the vertical displacement (dy) for the S-bend.
    # The top arm starts High and goes Low, so dy is negative.
    dy = y_top_waist - y_top_start

    # 3. Build Top Arm (Down then Up)
    # Converging section: S-bend going down
    t1 = c << gf.components.bend_s(size=(half_length, dy), cross_section=xs)
    t1.move((0, y_top_start))
    
    # Diverging section: S-bend going up (reverse displacement)
    t2 = c << gf.components.bend_s(size=(half_length, -dy), cross_section=xs)
    t2.connect("o1", t1.ports["o2"])

    # 4. Build Bottom Arm (Up then Down)
    # Symmetric start position
    y_bot_start = -y_top_start
    
    # Converging section: S-bend going up (displacement is -dy, which is positive)
    b1 = c << gf.components.bend_s(size=(half_length, -dy), cross_section=xs)
    b1.move((0, y_bot_start))
    
    # Diverging section: S-bend going down (displacement is dy, which is negative)
    b2 = c << gf.components.bend_s(size=(half_length, dy), cross_section=xs)
    b2.connect("o1", b1.ports["o2"])

    # 5. Expose Ports
    # Ports o1, o2 are inputs (left). Ports o3, o4 are outputs (right).
    c.add_port("o1", port=t1.ports["o1"])
    c.add_port("o2", port=b1.ports["o1"])
    c.add_port("o3", port=t2.ports["o2"])
    c.add_port("o4", port=b2.ports["o2"])

    return c

if __name__ == "__main__":
    device = adiabatic_coupler()
    device.write_gds("adiabatic_coupler.gds")