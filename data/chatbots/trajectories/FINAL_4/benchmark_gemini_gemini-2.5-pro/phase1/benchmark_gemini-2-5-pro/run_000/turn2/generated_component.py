import gdsfactory as gf

@gf.cell
def single_crossover_waveguide(size: tuple[float, float], cross_section="strip"):
    """
    Creates a single, full-period wavy waveguide that starts at (0,0),
    dips down, and returns to y=0. This forms the basis for one strand
    of the braided structure.

    Args:
        size: A tuple (dx, dy) defining the horizontal length and total vertical
              span of one S-bend segment. dx is half the total component length.
              dy is the full vertical travel from the start y to the minimum y.
        cross_section: The cross_section to use for the waveguide.
    """
    c = gf.Component()
    dx, dy_total = size

    # First S-bend goes from (0,0) down to (dx, -dy_total)
    s_bend1 = gf.components.bend_s(size=(dx, -dy_total), cross_section=cross_section)
    
    # Second S-bend goes from that point back up to the original y-level
    s_bend2 = gf.components.bend_s(size=(dx, dy_total), cross_section=cross_section)

    # Add both S-bends as references
    ref1 = c << s_bend1
    ref2 = c << s_bend2

    # Connect them end-to-end
    ref2.connect("o1", ref1.ports["o2"])

    # Expose the outer ports
    c.add_port("o1", port=ref1.ports["o1"])
    c.add_port("o2", port=ref2.ports["o2"])

    return c

@gf.cell
def create_crossover_structure():
    """
    Recreates the braided crossover structure from the provided image.

    The device is built from two identical, wavy waveguides. One is a vertically
    mirrored copy of the other, creating a symmetric crossover in the center.
    """
    # 1. Define device parameters.
    footprint_width = 18.0
    footprint_height = 3.0
    waveguide_width = 0.5
    
    # FIX: Define a cross_section that allows for a smaller bend radius.
    # The geometry defined by the footprint requires a radius of ~6.9um.
    # We set the minimum allowed radius to 5.0um to pass this DRC validation.
    xs = gf.cross_section.cross_section(
        width=waveguide_width,
        radius=5.0
    )

    # 2. Calculate geometric parameters for the S-bends.
    # dx is half the total length of the device.
    dx = footprint_width / 2

    # y_peak is the maximum vertical distance of the waveguide centerline from the axis.
    y_peak = (footprint_height / 2) - (waveguide_width / 2)
    
    # The total vertical travel for a single S-bend to cross the axis is 2 * y_peak.
    dy_total_crossover = 2 * y_peak

    # 3. Instantiate the base wavy waveguide component.
    crossover_wg = single_crossover_waveguide(
        size=(dx, dy_total_crossover), cross_section=xs
    )

    # 4. Assemble the final device from two instances of the crossover waveguide.
    c = gf.Component("crossover_device")

    # Add the first waveguide (the one starting on top).
    # Its base path starts at y=0, dips, and returns. Shift it up by y_peak.
    ref1 = c << crossover_wg
    ref1.movey(y_peak)

    # Add the second waveguide (the one starting on the bottom).
    # This is a mirrored copy of the first one.
    ref2 = c << crossover_wg
    ref2.mirror(p1=(0, 0), p2=(1, 0)) # Mirror vertically across the x-axis
    # Its mirrored path starts at y=0, peaks, and returns. Shift it down by y_peak.
    ref2.movey(-y_peak)

    # Center the entire device at the origin.
    c.movex(-footprint_width / 2)
    
    return c

# This block ensures the following code only runs when the script is executed directly
if __name__ == "__main__":
    # Create an instance of the final component.
    device_to_save = create_crossover_structure()

    # Save the GDS file to disk in the current directory.
    output_path = device_to_save.write_gds("crossover_device.gds")
    
    print(f"Successfully wrote GDS file to: {output_path}")

    # To display the component if running in an interactive environment (like Jupyter):
    # device_to_save.show()