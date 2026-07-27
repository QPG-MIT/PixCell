import gdsfactory as gf
from gdsfactory.typings import CrossSectionSpec

@gf.cell
def double_s_bend_coupler(
    width: float = 0.5,
    gap: float = 0.5,
    straight_io_length: float = 10.0,
    straight_center_length: float = 60.0,
    cross_section: CrossSectionSpec = "strip",
) -> gf.Component:
    """
    Creates a device with two parallel waveguides that curve outwards at both ends.
    It replicates the geometry shown in the image with a fixed footprint.

    The overall footprint is 120um (width) x 4um (height) as per the problem constraints.

    Args:
        width: Width of the waveguides.
        gap: Gap between the two parallel waveguides in the central section.
        straight_io_length: Length of the straight sections at the input/output ports.
        straight_center_length: Length of the straight section in the middle of the device.
        cross_section: Specification for the waveguide cross-section.

    Returns:
        A GDSFactory component representing the double S-bend coupler.
    """
    c = gf.Component("double_s_bend_coupler")
    xs = gf.get_cross_section(cross_section, width=width)

    # Device footprint constraints from the problem statement
    _total_width = 120.0
    _total_height = 4.0

    # Calculate vertical displacement for each S-bend (dy_s)
    # This is the vertical distance between the centerline of an outer waveguide
    # and the centerline of an inner waveguide.
    dy_s = (_total_height - (2 * width) - gap) / 2

    # Calculate horizontal length for each S-bend (dx_s)
    # The total width is composed of 2 I/O straights, 2 S-bends, and 1 central straight.
    dx_s = (_total_width - (2 * straight_io_length) - straight_center_length) / 2

    # Validate calculated dimensions
    if dx_s <= 0 or dy_s <= 0:
        raise ValueError(
            f"Invalid dimensions for S-bend. dx_s={dx_s:.2f}, dy_s={dy_s:.2f}. "
            "Please adjust `width`, `gap`, `straight_io_length`, or `straight_center_length` "
            "to fit within the required 120x4um footprint."
            f"Current settings: width={width}, gap={gap}, straight_io_length={straight_io_length}, straight_center_length={straight_center_length}"
        )

    # --- Top Path Construction ---
    # 1. Left Input Straight
    wg_io_left_top = c << gf.components.straight(length=straight_io_length, cross_section=xs)
    # Position the first component's centerline at the correct Y-coordinate for the top outer waveguide
    wg_io_left_top.movey((_total_height - width) / 2)

    # 2. Left S-bend (curves downwards towards the center)
    s_bend_left_top = c << gf.components.bend_s(size=(dx_s, -dy_s), cross_section=xs)
    s_bend_left_top.connect("o1", wg_io_left_top.ports["o2"])

    # 3. Central Straight
    wg_center_top = c << gf.components.straight(length=straight_center_length, cross_section=xs)
    wg_center_top.connect("o1", s_bend_left_top.ports["o2"])

    # 4. Right S-bend (curves upwards towards the outer edge)
    s_bend_right_top = c << gf.components.bend_s(size=(dx_s, dy_s), cross_section=xs)
    s_bend_right_top.connect("o1", wg_center_top.ports["o2"])

    # 5. Right Output Straight
    wg_io_right_top = c << gf.components.straight(length=straight_io_length, cross_section=xs)
    wg_io_right_top.connect("o1", s_bend_right_top.ports["o2"])

    # --- Bottom Path Construction ---
    # 1. Left Input Straight
    wg_io_left_bottom = c << gf.components.straight(length=straight_io_length, cross_section=xs)
    # Position the first component's centerline at the correct Y-coordinate for the bottom outer waveguide
    wg_io_left_bottom.movey(-(_total_height - width) / 2)

    # 2. Left S-bend (curves upwards towards the center)
    s_bend_left_bottom = c << gf.components.bend_s(size=(dx_s, dy_s), cross_section=xs)
    s_bend_left_bottom.connect("o1", wg_io_left_bottom.ports["o2"])

    # 3. Central Straight
    wg_center_bottom = c << gf.components.straight(length=straight_center_length, cross_section=xs)
    wg_center_bottom.connect("o1", s_bend_left_bottom.ports["o2"])

    # 4. Right S-bend (curves downwards towards the outer edge)
    s_bend_right_bottom = c << gf.components.bend_s(size=(dx_s, -dy_s), cross_section=xs)
    s_bend_right_bottom.connect("o1", wg_center_bottom.ports["o2"])

    # 5. Right Output Straight
    wg_io_right_bottom = c << gf.components.straight(length=straight_io_length, cross_section=xs)
    wg_io_right_bottom.connect("o1", s_bend_right_bottom.ports["o2"])

    # --- Add Ports to the Component for external connectivity ---
    c.add_port("o1_top", port=wg_io_left_top.ports["o1"])
    c.add_port("o2_top", port=wg_io_right_top.ports["o2"])
    c.add_port("o1_bottom", port=wg_io_left_bottom.ports["o1"])
    c.add_port("o2_bottom", port=wg_io_right_bottom.ports["o2"])

    # Center the entire component horizontally and vertically
    c.center()

    return c

# Example usage and verification
if __name__ == "__main__":
    # Create the component with default parameters
    component = double_s_bend_coupler()

    # Create a component for footprint verification (without port extensions)
    # We pass port_extension=0 to the cross_section to get the exact geometry size
    # without any default extensions that GDSFactory might add to ports.
    component_no_extension = double_s_bend_coupler(
        cross_section=gf.cross_section.strip(port_extension=0)
    )

    # Print component information
    print(f"Component bounding box (with default port extensions): {component.bbox}")
    print(f"Component width (with default port extensions): {component.xsize:.3f} um")
    print(f"Component height (with default port extensions): {component.ysize:.3f} um")
    
    print(f"\nComponent bounding box (without port extensions): {component_no_extension.bbox}")
    print(f"Component width (without port extensions): {component_no_extension.xsize:.3f} um")
    print(f"Component height (without port extensions): {component_no_extension.ysize:.3f} um")

    # Expected output for `component_no_extension` should closely match the footprint:
    # Component width (without port extensions): 120.000 um
    # Component height (without port extensions): 4.000 um

    # Save the component to a GDSII file
    # component.write_gds("double_s_bend_coupler.gds")

    # To visualize the component (requires KLayout to be installed and configured with gdsfactory)
    # component.show()