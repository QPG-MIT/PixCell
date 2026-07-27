import gdsfactory as gf

@gf.cell
def create_directional_coupler():
    """
    Creates a directional coupler by composing primitive components based on
    the provided image and footprint constraints.
    """
    # --- 1. Parameter Derivation ---
    # Based on footprint [120, 4] um and visual analysis.
    footprint_x = 120.0
    footprint_y = 4.0

    wg_width = 0.5  # Standard waveguide width
    gap = 0.2       # Assumed coupling gap

    # The straight coupling section is set to half the total device length.
    coupling_length = footprint_x / 2.0

    # The remaining length is divided between the two S-bend transition sections.
    s_bend_dx = (footprint_x - coupling_length) / 2.0

    # The total bounding box height is the center-to-center separation of the
    # outer ports plus one waveguide width.
    y_separation_io = footprint_y - wg_width

    # The center-to-center separation in the coupling region.
    y_separation_coupling = wg_width + gap

    # Each S-bend must bridge half of the total change in vertical separation.
    s_bend_dy = (y_separation_io - y_separation_coupling) / 2.0

    # --- 2. Component Assembly ---
    c = gf.Component("directional_coupler_assembled")

    # Define a common cross-section for all waveguide components.
    xs = gf.cross_section.cross_section(width=wg_width)

    # Create the central parallel waveguide section. This component has four
    # ports: o1 (top-left), o2 (bottom-left), o3 (top-right), o4 (bottom-right).
    coupler_core = c << gf.components.coupler_straight(
        length=coupling_length, gap=gap, cross_section=xs
    )

    # Create the S-bend primitive that will be used for all four transitions.
    s_bend = gf.components.bend_s(size=(s_bend_dx, s_bend_dy), cross_section=xs)

    # Add and connect the input S-bends (left side).
    bend_in_top = c << s_bend
    bend_in_bottom = c << s_bend

    bend_in_top.mirror()  # Mirror across Y-axis to point left.
    bend_in_bottom.mirror()  # Mirror across Y-axis...
    bend_in_bottom.mirror_y() # ...and then across X-axis for the bottom path.

    bend_in_top.connect("o2", coupler_core.ports["o1"])
    bend_in_bottom.connect("o2", coupler_core.ports["o2"])

    # Add and connect the output S-bends (right side).
    bend_out_top = c << s_bend
    bend_out_bottom = c << s_bend

    bend_out_bottom.mirror_y()  # Mirror across X-axis for the bottom path.

    bend_out_top.connect("o1", coupler_core.ports["o3"])
    bend_out_bottom.connect("o1", coupler_core.ports["o4"])

    # --- 3. Port Definition ---
    # Add external ports to the assembled component from the unconnected
    # ends of the S-bends.
    c.add_port("o1", port=bend_in_top.ports["o1"])
    c.add_port("o2", port=bend_in_bottom.ports["o1"])
    c.add_port("o3", port=bend_out_top.ports["o2"])
    c.add_port("o4", port=bend_out_bottom.ports["o2"])

    return c

# This block ensures that the following code runs only when the script is
# executed directly, not when imported as a module.
if __name__ == "__main__":
    # Create an instance of the device.
    device = create_directional_coupler()
    
    # **FIX:** Add the command to write the component to a GDS file.
    # This was the missing step.
    device.write_gds("directional_coupler.gds")

    # Optional: show the component in a viewer
    device.show()