import gdsfactory as gf

@gf.cell
def create_interleaver_device():
    """
    Recreates the waveguide interleaver device using GDSFactory.

    The device routes two separate groups of waveguides (top and bottom)
    into a single, interleaved output group. This is achieved by defining
    the start and end components and using the automated `route_single`
    function to generate the complex crossover paths.
    """
    # 1. Define Design Parameters
    n_lines = 5
    width = 0.5
    gap = 0.4
    pitch = width + gap
    
    # FIX: Increased min_bend_radius from 8.0 to 10.0 to satisfy the
    # default cross_section's minimum radius constraint.
    min_bend_radius = 10.0
    
    initial_straight_len = 20.0
    final_straight_len = 40.0
    # Vertical separation between the centerlines of the top and bottom groups
    group_separation = 15.0
    # Horizontal distance allocated for the routing crossover
    routing_x_distance = 40.0

    # The default cross_section has radius_min=10.0
    xs = gf.cross_section.cross_section(width=width)
    c = gf.Component("WaveguideInterleaver")

    # 2. Create and place the initial bent waveguides (Left Side)
    # These lists will store the output ports that need to be routed
    top_source_ports = []
    bottom_source_ports = []

    for i in range(n_lines):
        radius = min_bend_radius + i * pitch

        # --- Top Group ---
        bend_top = gf.components.bend_euler(radius=radius, angle=90, cross_section=xs)
        straight_top = gf.components.straight(length=initial_straight_len, cross_section=xs)

        b_ref_t = c << bend_top
        s_ref_t = c << straight_top

        # Position the top bends vertically, spaced apart
        b_ref_t.movey(group_separation / 2 + (n_lines - 1) * pitch / 2 + i * pitch)
        s_ref_t.connect("o1", b_ref_t.ports["o2"])
        top_source_ports.append(s_ref_t.ports["o2"])

        # --- Bottom Group ---
        bend_bottom = gf.components.bend_euler(radius=radius, angle=-90, cross_section=xs)
        straight_bottom = gf.components.straight(length=initial_straight_len, cross_section=xs)

        b_ref_b = c << bend_bottom
        s_ref_b = c << straight_bottom
        
        # Position the bottom bends vertically
        b_ref_b.movey(-group_separation / 2 - (n_lines - 1) * pitch / 2 - i * pitch)
        s_ref_b.connect("o1", b_ref_b.ports["o2"])
        bottom_source_ports.append(s_ref_b.ports["o2"])


    # 3. Create and place the final straight waveguides (Right Side)
    # These lists will store the input ports that are the routing destinations
    destination_ports = []
    
    # Calculate the starting X-position for the final straights
    final_x_pos = top_source_ports[0].x + routing_x_distance

    # Total number of output lines is 2 * n_lines
    total_lines = 2 * n_lines
    for i in range(total_lines):
        # Calculate Y position for each final waveguide, centered around y=0
        y_pos = (i - (total_lines - 1) / 2) * pitch
        
        straight_final = c << gf.components.straight(length=final_straight_len, cross_section=xs)
        straight_final.move((final_x_pos, y_pos))
        destination_ports.append(straight_final.ports["o1"])

    # 4. Route the connections
    # We interleave the outputs: top[0]->dest[0], bottom[0]->dest[1], top[1]->dest[2], etc.
    for i in range(n_lines):
        # Route from top source port
        gf.routing.route_single(c, top_source_ports[i], destination_ports[2 * i], cross_section=xs)
        
        # Route from bottom source port
        gf.routing.route_single(c, bottom_source_ports[i], destination_ports[2 * i + 1], cross_section=xs)

    return c

# --- Main execution block ---
if __name__ == "__main__":
    # Instantiate the component by calling the function
    my_device = create_interleaver_device()
    
    # Write the component to a GDS file
    my_device.write_gds("device_recreation.gds")

    # Optional: show the component in the KLayout viewer if installed
    my_device.show()