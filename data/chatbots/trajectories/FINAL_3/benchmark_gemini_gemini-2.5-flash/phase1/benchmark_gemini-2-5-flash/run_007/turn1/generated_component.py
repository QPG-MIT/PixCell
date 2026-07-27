import gdsfactory as gf

@gf.cell
def my_device() -> gf.Component:
    """
    Recreates the geometry from the provided image using GDSFactory parametric functions.

    The device consists of two parallel central waveguides connected to four
    S-bends at its ends, fitting within a [120, 4] um footprint.
    """
    c = gf.Component("s_bend_waveguide_splitter")

    # Define the waveguide cross-section
    # Assuming a standard width of 0.5 um on layer (1, 0)
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))

    # --- Derived Parameters from Footprint [120, 4] um ---
    total_length = 120  # Total horizontal length of the device
    total_height = 4    # Total vertical height of the device

    # Horizontal extent (dx) of each S-bend
    # Estimated such that the central straight section has a reasonable length.
    dx_s_bend = 45  # um

    # Length of the central straight waveguide segments
    length_straight_center = total_length - (2 * dx_s_bend)  # 120 - (2 * 45) = 30 um

    # Vertical displacement (dy) for each S-bend
    # (Total height / 2) - (waveguide_width / 2) = centerline of outer path
    # (Waveguide_gap / 2) + (waveguide_width / 2) = centerline of inner path
    # dy_s_bend = (2 - 0.5/2) - (0.5/2 + 0.5/2) = 1.75 - 0.5 = 1.25 um
    dy_s_bend = 1.25  # um

    # 1. Create the two central straight waveguides
    # Position them symmetrically around the x-axis.
    # The 'o1' port of the straight_top_ref will be at (-length_straight_center/2, 0.5)
    straight_top_ref = c << gf.components.straight(length=length_straight_center, cross_section=xs)
    straight_top_ref.move((-length_straight_center / 2, 0.5))

    # The 'o1' port of the straight_bottom_ref will be at (-length_straight_center/2, -0.5)
    straight_bottom_ref = c << gf.components.straight(length=length_straight_center, cross_section=xs)
    straight_bottom_ref.move((-length_straight_center / 2, -0.5))

    # 2. Create and connect the left S-bends
    # Top-left S-bend: Connects an outer-Y input port to the inner-Y 'o1' of the top straight.
    # The 'dy' parameter needs to be negative because the waveguide goes from a higher Y to a lower Y.
    bend_s_TL_ref = c << gf.components.bend_s(size=(dx_s_bend, -dy_s_bend), cross_section=xs)
    bend_s_TL_ref.connect("o2", straight_top_ref.ports["o1"])

    # Bottom-left S-bend: Connects an outer-Y input port to the inner-Y 'o1' of the bottom straight.
    # The 'dy' parameter needs to be positive because the waveguide goes from a lower Y to a higher Y.
    bend_s_BL_ref = c << gf.components.bend_s(size=(dx_s_bend, dy_s_bend), cross_section=xs)
    bend_s_BL_ref.connect("o2", straight_bottom_ref.ports["o1"])

    # 3. Create and connect the right S-bends
    # Top-right S-bend: Connects the inner-Y 'o2' of the top straight to an outer-Y output port.
    # The 'dy' parameter needs to be positive.
    bend_s_TR_ref = c << gf.components.bend_s(size=(dx_s_bend, dy_s_bend), cross_section=xs)
    bend_s_TR_ref.connect("o1", straight_top_ref.ports["o2"])

    # Bottom-right S-bend: Connects the inner-Y 'o2' of the bottom straight to an outer-Y output port.
    # The 'dy' parameter needs to be negative.
    bend_s_BR_ref = c << gf.components.bend_s(size=(dx_s_bend, -dy_s_bend), cross_section=xs)
    bend_s_BR_ref.connect("o1", straight_bottom_ref.ports["o2"])

    # 4. Add external ports to the main component for device interface
    c.add_port("o1_top", port=bend_s_TL_ref.ports["o1"])
    c.add_port("o1_bottom", port=bend_s_BL_ref.ports["o1"])
    c.add_port("o2_top", port=bend_s_TR_ref.ports["o2"])
    c.add_port("o2_bottom", port=bend_s_BR_ref.ports["o2"])

    return c

if __name__ == "__main__":
    # Create the device component
    device = my_device()

    # Write the GDS file for the device
    device.write_gds("my_device.gds")

    # Optional: Display the component in KLayout or other GDS viewer
    # device.show()

    # Optional: Print bounding box to verify footprint
    # bbox = device.bbox()
    # print(f"Device Bounding Box: {bbox}")
    # x_span = bbox[1][0] - bbox[0][0]
    # y_span = bbox[1][1] - bbox[0][1]
    # print(f"Calculated X span: {x_span} um (Expected: 120 um)") # Should be 120
    # print(f"Calculated Y span: {y_span} um (Expected: 4 um)")   # Should be 4