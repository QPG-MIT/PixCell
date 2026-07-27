import gdsfactory as gf

@gf.cell
def create_coupler_crossing():
    """
    Creates a crossing directional coupler (X-coupler).

    This device consists of two S-bends that cross the central axis,
    allowing light to couple from the top input to the bottom output,
    and from the bottom input to the top output.
    """
    # --- 1. Parameter Definition ---
    # Derived from the footprint constraint and visual analysis.
    footprint_x = 120.0
    footprint_y = 4.0
    wg_width = 0.5

    # The vertical separation between the centers of the input/output ports.
    port_separation_y = footprint_y - wg_width

    # The size of the S-bend defines its end-to-end displacement.
    # dx is the full length of the device.
    # dy is the full vertical separation between ports.
    s_bend_size = (footprint_x, port_separation_y)

    # --- 2. Component Assembly ---
    c = gf.Component("coupler_crossing")
    xs = gf.cross_section.cross_section(width=wg_width)

    # Define the primitive S-bend component that will form both paths.
    s_bend = gf.components.bend_s(size=s_bend_size, cross_section=xs)

    # Instantiate the two S-bend paths as references.
    # Path 1: Connects bottom-left to top-right.
    path_bot_to_top = c << s_bend
    # Path 2: Connects top-left to bottom-right.
    path_top_to_bot = c << s_bend

    # --- 3. Orientation and Positioning ---
    # Path 2 needs to be mirrored vertically to create the crossing shape.
    path_top_to_bot.mirror_y()

    # Position the two paths to be centered at (0,0). Since the 'o1' port of the
    # s_bend component is at (0,0), setting the reference's origin effectively
    # places the 'o1' port at the desired location.
    path_bot_to_top.origin = (-footprint_x / 2, -port_separation_y / 2)
    path_top_to_bot.origin = (-footprint_x / 2, +port_separation_y / 2)

    # --- 4. Port Definition ---
    # Expose the external ports of the final component with standard naming.
    c.add_port("o1", port=path_top_to_bot.ports["o1"])  # Top-left
    c.add_port("o2", port=path_bot_to_top.ports["o1"])  # Bottom-left
    c.add_port("o3", port=path_bot_to_top.ports["o2"])  # Top-right
    c.add_port("o4", port=path_top_to_bot.ports["o2"])  # Bottom-right

    return c

if __name__ == "__main__":
    # Create an instance of the device cell.
    device = create_coupler_crossing()
    
    # Write the component geometry to a GDSII file.
    device.write_gds("coupler_crossing.gds")

    # Optional: Display the component in the KLayout-based viewer.
    device.show()