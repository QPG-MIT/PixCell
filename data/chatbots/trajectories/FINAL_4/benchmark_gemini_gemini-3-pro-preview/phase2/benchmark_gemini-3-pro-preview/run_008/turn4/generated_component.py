import gdsfactory as gf

@gf.cell
def adiabatic_coupler():
    c = gf.Component()
    
    # 1. Dimensions & Constraints
    # The device footprint is constrained to 18um x 3um.
    total_length = 18.0
    total_height = 3.0
    
    # Visual analysis adjustments:
    # - Width increased to 1.0um so the input gap roughly equals the waveguide width (1:1 ratio).
    # - Min gap reduced to 0.1um to create the tight "pinch" seen in the target waist.
    wg_width = 1.0
    min_gap = 0.1
    
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))

    # 2. Geometric Calculations
    # Split the length into converging (input -> waist) and diverging (waist -> output) halves.
    half_length = total_length / 2.0
    
    # Calculate Y positions relative to the center line (y=0) to fit exactly in 3um height.
    
    # Start Position: Outer edges align with +/- 1.5um.
    # Top WG Center Y = (Total Height / 2) - (Waveguide Width / 2)
    # 1.5 - 0.5 = 1.0
    y_top_start = (total_height / 2.0) - (wg_width / 2.0)
    
    # Waist Position: Waveguides are separated by the minimum gap (0.1um).
    # Top WG Center Y = (Gap / 2) + (Waveguide Width / 2)
    # 0.05 + 0.5 = 0.55
    y_top_waist = (min_gap / 2.0) + (wg_width / 2.0)
    
    # Calculate the vertical displacement (dy) for the S-bend.
    # Top arm goes from 1.0 to 0.55, so dy is negative.
    dy_top = y_top_waist - y_top_start

    # 3. Build Top Arm
    # Converging section: S-bend going down
    t1 = c << gf.components.bend_s(size=(half_length, dy_top), cross_section=xs)
    t1.move((0, y_top_start))
    
    # Diverging section: S-bend going up (reverse displacement)
    t2 = c << gf.components.bend_s(size=(half_length, -dy_top), cross_section=xs)
    t2.connect("o1", t1.ports["o2"])

    # 4. Build Bottom Arm (Symmetric)
    y_bot_start = -y_top_start
    # Bottom arm displacement is positive (up towards center)
    dy_bot = -dy_top
    
    # Converging section
    b1 = c << gf.components.bend_s(size=(half_length, dy_bot), cross_section=xs)
    b1.move((0, y_bot_start))
    
    # Diverging section
    b2 = c << gf.components.bend_s(size=(half_length, -dy_bot), cross_section=xs)
    b2.connect("o1", b1.ports["o2"])

    # 5. Expose Ports
    c.add_port("o1", port=t1.ports["o1"])
    c.add_port("o2", port=b1.ports["o1"])
    c.add_port("o3", port=t2.ports["o2"])
    c.add_port("o4", port=b2.ports["o2"])

    return c

if __name__ == "__main__":
    device = adiabatic_coupler()
    device.write_gds("adiabatic_coupler.gds")