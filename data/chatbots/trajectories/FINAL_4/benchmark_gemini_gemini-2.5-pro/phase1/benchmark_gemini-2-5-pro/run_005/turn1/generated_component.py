import gdsfactory as gf

@gf.cell
def create_wavy_coupler():
    """
    Creates a wavy coupler geometry based on the provided image and footprint.

    The device consists of two identical, vertically mirrored wavy waveguides.
    Each wavy waveguide is constructed by connecting two S-bends back-to-back.
    """
    # 1. Define device parameters from footprint and visual inspection
    footprint_width = 18.0
    footprint_height = 3.0

    # Assume a standard waveguide width and a small minimum gap, which are
    # reasonable for such a structure.
    waveguide_width = 0.6
    min_gap = 0.3

    # 2. Calculate geometric parameters for the primitives
    # The total width is composed of two S-bends, so each has half the width.
    s_bend_dx = footprint_width / 2.0

    # The total height determines the initial separation of the waveguides.
    # Total height = (center_sep * 2) + waveguide_width
    center_separation_at_ends = (footprint_height - waveguide_width) / 2

    # The vertical amplitude of the wave (H) is determined by the difference
    # between the gap at the ends and the gap in the middle.
    gap_at_ends = 2 * center_separation_at_ends
    # We want to find H such that the middle gap is min_gap.
    # min_gap = gap_at_ends - 2*H => 2*H = gap_at_ends - min_gap
    s_bend_dy = (gap_at_ends - min_gap) / 2

    # 3. Define the cross-section to be used for the waveguides
    xs = gf.cross_section.cross_section(width=waveguide_width)

    # 4. Build the single wavy path by connecting two S-bends.
    # This will be used as a building block for both top and bottom parts.
    c_wave_unit = gf.Component("wavy_path_unit")
    
    # First S-bend curves inwards (negative dy)
    bend1 = c_wave_unit << gf.components.bend_s(
        size=(s_bend_dx, -s_bend_dy), cross_section=xs
    )
    # Second S-bend curves outwards to return to the original y-level (positive dy)
    bend2 = c_wave_unit << gf.components.bend_s(
        size=(s_bend_dx, s_bend_dy), cross_section=xs
    )

    # Connect the two bends seamlessly
    bend2.connect("o1", bend1.ports["o2"])
    
    # Add ports to the reusable wavy unit
    c_wave_unit.add_port("o1", port=bend1.ports["o1"])
    c_wave_unit.add_port("o2", port=bend2.ports["o2"])


    # 5. Assemble the final device from two instances of the wavy unit
    c = gf.Component("wavy_coupler_device")

    # Add the top waveguide and move it to its correct vertical position
    top_wave = c << c_wave_unit
    top_wave.movey(center_separation_at_ends)

    # Add the bottom waveguide, mirror it vertically, and move it into position
    bottom_wave = c << c_wave_unit
    bottom_wave.mirror(p1=(0, 0), p2=(1, 0))  # Mirror across the x-axis
    bottom_wave.movey(-center_separation_at_ends)

    # Expose the ports of the top and bottom waveguides for connectivity
    c.add_port("o1", port=top_wave.ports["o1"])
    c.add_port("o2", port=top_wave.ports["o2"])
    c.add_port("o3", port=bottom_wave.ports["o1"])
    c.add_port("o4", port=bottom_wave.ports["o2"])

    return c

# Main execution block to generate and display the GDS
if __name__ == "__main__":
    device = create_wavy_coupler()
    device.show()
    
    # This line is now active and will produce the GDS file.
    device.write_gds("wavy_coupler.gds")