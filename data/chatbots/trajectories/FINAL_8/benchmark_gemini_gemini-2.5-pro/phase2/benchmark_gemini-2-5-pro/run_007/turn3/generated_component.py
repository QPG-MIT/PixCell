import gdsfactory as gf
from gdsfactory.cross_section import Section

# It's good practice to create reusable building blocks in their own functions.
@gf.cell
def create_flaring_section(
    bend_radius: float,
    straight_length: float,
    line_width: float,
    gap: float,
    n_lines: int,
    thick_band_width: float,
) -> gf.Component:
    """Creates the top U-shaped flaring section made of a thick band and N lines."""
    c = gf.Component("flaring_section")
    pitch = line_width + gap

    # 1. Define the path for the flared shape (a wide "hat" shape)
    # The path starts and ends pointing vertically upwards.
    path = gf.Path()
    path.append(gf.path.euler(radius=bend_radius, angle=-90))
    path.append(gf.path.straight(length=straight_length))
    path.append(gf.path.euler(radius=bend_radius, angle=90))

    # 2. Define the cross-section for this component
    # Offsets are relative to the center of the thick band (y=0 in this component)
    sections = [Section(width=thick_band_width, offset=0, layer=(1, 0))]

    # Calculate starting y-offset for the thin lines stacked above the band
    current_y = 0.5 * thick_band_width + gap + 0.5 * line_width
    for _ in range(n_lines):
        sections.append(Section(width=line_width, offset=current_y, layer=(1, 0)))
        current_y += pitch
    
    xs_flare = gf.cross_section.CrossSection(sections=sections)

    # 3. Extrude the path with the cross-section
    c.add_ref(gf.path.extrude(path, cross_section=xs_flare))
    return c


@gf.cell
def create_device():
    """
    Creates the target device by assembling three parts:
    1. A top flaring section.
    2. A bottom flaring section (mirrored top).
    3. A central section of straight lines.
    """
    c = gf.Component("final_device")

    # --- Define Device Parameters based on Footprint ---
    total_width = 120.0
    total_height = 4.0

    n_outer_lines = 4
    n_center_lines = 4
    
    # Calculate widths and gaps to fit the total height based on component stacking.
    # Let w be the base unit (thin line width). Assume gap=w, band_gap=w, thick_band_w=3w.
    # Total Height H = (center_group_h) + 2*(band_gap) + 2*(thick_band_w) + 2*(outer_group_h)
    # center_group_h = 4w + 3g = 7w
    # outer_group_h = 4w + 3g = 7w
    # H = 7w + 2*w + 2*(3w) + 2*(7w) = 7w + 2w + 6w + 14w = 29w -- Wait, this is double counting.
    # Let's sum from center y=0 upwards:
    # Half of center group = (4w+3g)/2 = 3.5w
    # Band gap = w
    # Thick band = 3w
    # Gap = w
    # Outer group = 4w+3g = 7w
    # Total half-height = 3.5w + w + 3w + w + 7w = 15.5w
    # Total height H = 2 * 15.5w = 31w
    
    line_width = total_height / 31
    gap = line_width
    band_gap = line_width
    thick_band_width = 3 * line_width
    pitch = line_width + gap

    # Calculate lengths to fit total width
    bend_radius = 15.0
    straight_length = total_width - 2 * bend_radius

    # --- 1. Create and Place the Flaring Sections ---
    
    # Create the reusable flaring component
    flare_section = create_flaring_section(
        bend_radius=bend_radius,
        straight_length=straight_length,
        line_width=line_width,
        gap=gap,
        n_lines=n_outer_lines,
        thick_band_width=thick_band_width,
    )

    # Calculate the vertical position for the top flaring section.
    # Its local y=0 is the center of its thick band. We need to place this correctly.
    center_lines_half_height = (n_center_lines * line_width + (n_center_lines - 1) * gap) / 2
    y_pos_top_flare_center = center_lines_half_height + band_gap + 0.5 * thick_band_width
    
    # Add top flare, positioned correctly.
    top_flare = c.add_ref(flare_section)
    top_flare.movey(y_pos_top_flare_center)

    # Add bottom flare (mirrored and moved)
    bottom_flare = c.add_ref(flare_section)
    bottom_flare.mirror_y()
    bottom_flare.movey(-y_pos_top_flare_center)

    # --- 2. Create and Place the Central Straight Lines ---
    
    # The central lines run the entire width of the device
    center_straight_width = total_width

    # Calculate y-positions for the central lines, centered around y=0
    start_y_center = - (n_center_lines - 1) * pitch / 2
    for i in range(n_center_lines):
        y_pos = start_y_center + i * pitch
        rect = gf.components.rectangle(
            size=(center_straight_width, line_width),
            layer=(1,0),
            centered=True
        )
        c.add_ref(rect).movey(y_pos)

    return c

if __name__ == "__main__":
    device_to_save = create_device()
    device_to_save.write_gds("recreated_device.gds")
    print("Successfully wrote GDS file to 'recreated_device.gds'")
    # You can uncomment the following line to open the GDS in KLayout for viewing
    # device_to_save.show()