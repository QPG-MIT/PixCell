import gdsfactory as gf
from gdsfactory.cross_section import Section

@gf.cell
def create_single_line_waist(
    length: float,
    waist_length: float,
    dy: float,
    cross_section,
) -> gf.Component:
    """
    Creates a single wide-narrow-wide path using two S-bends and a straight.
    The path starts at y=0 and dips down by `dy` at the waist.

    Args:
        length: Total horizontal length of the structure.
        waist_length: Length of the central narrow straight section.
        dy: The vertical displacement of the bends (how far it dips).
        cross_section: The cross_section to extrude.
    """
    c = gf.Component()
    dx = (length - waist_length) / 2.0

    # Handle the case where there is no transition length
    if dx <= 1e-9: # Use a small tolerance for floating point
        s = gf.components.straight(length=length, cross_section=cross_section)
        s_ref = c << s
        c.add_port("o1", port=s_ref.ports["o1"])
        c.add_port("o2", port=s_ref.ports["o2"])
        return c

    # Create the segment components
    bend_in = gf.components.bend_s(size=(dx, -dy), cross_section=cross_section)
    straight_waist = gf.components.straight(length=waist_length, cross_section=cross_section)
    bend_out = gf.components.bend_s(size=(dx, dy), cross_section=cross_section)

    # Add references and connect them sequentially
    b1_ref = c << bend_in
    s_ref = c << straight_waist
    b2_ref = c << bend_out

    s_ref.connect("o1", b1_ref.ports["o2"])
    b2_ref.connect("o1", s_ref.ports["o2"])

    # Expose the start and end ports for the new component
    c.add_port("o1", port=b1_ref.ports["o1"])
    c.add_port("o2", port=b2_ref.ports["o2"])
    
    return c


@gf.cell
def create_multi_line_waist(
    num_lines: int,
    length: float,
    waist_length: float,
    line_width: float,
    pitch_start: float,
    pitch_waist: float,
    y_start_bottom: float,
    y_waist_bottom: float,
    layer,
) -> gf.Component:
    """
    Creates a set of lines that get closer together in the middle.
    Each line is a separate waist structure with a different vertical displacement.
    """
    c = gf.Component()
    
    xs_single_line = gf.cross_section.cross_section(width=line_width, layer=layer)
    
    for i in range(num_lines):
        y_start = y_start_bottom + i * pitch_start
        y_waist = y_waist_bottom + i * pitch_waist
        
        # dy is the total vertical displacement for this specific line
        dy = y_start - y_waist
        
        # Create the individual waist structure for this line
        single_line_component = create_single_line_waist(
            length=length,
            waist_length=waist_length,
            dy=dy,
            cross_section=xs_single_line
        )
        
        # Add the line and position it vertically at its starting y-coordinate
        line_ref = c << single_line_component
        line_ref.y = y_start
        
    return c


@gf.cell
def create_spool_device():
    """
    Creates the symmetric spool device using individual paths for each line
    in the outer sections to achieve the fanning/compression effect.
    Parameters are derived to match the target image and footprint [120.0, 4.0].
    """
    c = gf.Component("SpoolDevice")
    layer = (1, 0)
    
    # --- 1. Define Parameters from Analysis ---
    
    # Footprint constraints
    total_length = 120.0
    total_height_at_ends = 4.0
    waist_length = 60.0
    num_lines = 5
    grid_size = gf.get_active_pdk().grid_size # Typically 0.001 um

    # Vertical geometry based on 5 equal blocks (3 sections, 2 gaps) at ends
    block_height = total_height_at_ends / 5.0  # = 0.8 um
    gap_at_ends = block_height
    
    # --- FIX: Calculate line width and gap to be on-grid and have even dbu width ---
    # The total height of one 5-line section is 0.8um (800 dbu).
    # We need 5 lines and 4 gaps to fit in this space.
    # To avoid floating point issues and ensure the line_width is an even number
    # of database units (dbu), we define them explicitly.
    # Let line_width = 88 dbu = 0.088 um (even number)
    # Let line_gap_end = 90 dbu = 0.090 um
    # Total check: 5 * 88 + 4 * 90 = 440 + 360 = 800 dbu = 0.8 um. This works.
    
    line_width = 88 * grid_size  # 0.088 um
    line_gap_end = 90 * grid_size # 0.090 um
    pitch_end = line_width + line_gap_end
    
    # Geometry at the waist
    gap_at_waist = gap_at_ends / 2.0 # = 0.4 um
    # Ensure waist gap is also on-grid. 0.088/4 = 0.022 um (22 dbu, even), which is fine.
    line_gap_waist = gf.snap.snap_to_grid(line_width / 4, grid_factor=2)
    pitch_waist = line_width + line_gap_waist

    # --- 2. Calculate Y-coordinates for positioning ---
    
    # Middle bus lines are centered at y=0. Outermost line has its center at:
    y_center_bus_outermost = ( (num_lines - 1) / 2 ) * pitch_end
    # The top edge of this outermost line is at:
    y_edge_bus_top = y_center_bus_outermost + line_width / 2.0

    # Top section lines (at the ends of the device)
    # The bottom edge of the innermost line of the top section starts at:
    y_edge_top_section_bottom_at_ends = y_edge_bus_top + gap_at_ends
    # The center of this innermost line is at:
    y_center_top_section_innermost_at_ends = y_edge_top_section_bottom_at_ends + line_width / 2.0
    
    # Top section lines (at the waist of the device)
    # The bottom edge of the innermost line of the top section at the waist is at:
    y_edge_top_section_bottom_at_waist = y_edge_bus_top + gap_at_waist
    # The center of this innermost line is at:
    y_center_top_section_innermost_at_waist = y_edge_top_section_bottom_at_waist + line_width / 2.0

    # --- 3. Define Cross-Section for Middle Bus ---
    
    offsets = [ (i - (num_lines - 1) / 2) * pitch_end for i in range(num_lines) ]
    sections = [Section(width=line_width, offset=offset, layer=layer) for offset in offsets]
    xs_multi = gf.cross_section.cross_section(sections=sections)

    # --- 4. Create Child Components ---
    
    # Middle straight bus
    middle_bus = gf.components.straight(length=total_length, cross_section=xs_multi)
    
    # Top fanning section
    top_section = create_multi_line_waist(
        num_lines=num_lines,
        length=total_length,
        waist_length=waist_length,
        line_width=line_width,
        pitch_start=pitch_end,
        pitch_waist=pitch_waist,
        y_start_bottom=y_center_top_section_innermost_at_ends,
        y_waist_bottom=y_center_top_section_innermost_at_waist,
        layer=layer,
    )
    
    # --- 5. Assemble Final Device ---
    
    c << middle_bus
    c << top_section
    
    # Create bottom section by adding a mirrored reference of the top section
    bot_ref = c << top_section
    bot_ref.mirror_y() # Mirror across the x-axis
    
    c.flatten()
    return c


# --- Main execution block to generate the GDS file ---
if __name__ == "__main__":
    device_to_write = create_spool_device()
    device_to_write.write_gds("output.gds")
    print("GDS file 'output.gds' has been successfully generated.")
    
    # Optional: uncomment the line below to show the geometry in a viewer
    # device_to_write.show(show_ports=False)