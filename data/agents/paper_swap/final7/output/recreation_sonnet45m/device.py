"""
Stadium-shaped photonic structure with gaps
Primitives-only parametric GDSFactory script
"""
import gdsfactory as gf
import numpy as np

# Top-level tunables (function-defining knobs)
stadium_length = 3.0  # um - horizontal extent
stadium_width = 5.5  # um - vertical extent (footprint)
end_radius = 2.75  # um - radius of curved ends
gap_width = 0.52  # um - width of rectangular gaps
gap_height = 0.46  # um - height of rectangular gaps
gap_spacing_y = 0.68  # um - vertical spacing between gap rows
gap_spacing_x = 0.56  # um - horizontal spacing between gaps in a row

# Layer
layer = (1, 0)


@gf.cell
def stadium_with_gaps() -> gf.Component:
    """Stadium shape (racetrack) with rectangular gaps cut out."""
    c = gf.Component()

    # Create stadium as elliptical path
    # Stadium = two semicircles connected by straights
    straight_len = stadium_length - stadium_width  # center straight section length
    radius = stadium_width / 2

    # Create stadium outline using Path
    theta = np.linspace(0, 2*np.pi, 100)
    # Parametric stadium: left semicircle + top straight + right semicircle + bottom straight
    x_coords = []
    y_coords = []

    # Left semicircle (theta from pi/2 to -pi/2)
    for t in np.linspace(np.pi/2, -np.pi/2, 30):
        x_coords.append(straight_len/2 + radius*np.cos(t))
        y_coords.append(radius*np.sin(t))

    # Bottom straight
    for x in np.linspace(straight_len/2 + radius, stadium_length - radius, 5):
        x_coords.append(x)
        y_coords.append(-radius)

    # Right semicircle (theta from -pi/2 to pi/2)
    for t in np.linspace(-np.pi/2, np.pi/2, 30):
        x_coords.append(stadium_length - radius + radius*np.cos(t))
        y_coords.append(radius*np.sin(t))

    # Top straight
    for x in np.linspace(stadium_length - radius, straight_len/2 + radius, 5):
        x_coords.append(x)
        y_coords.append(radius)

    path_stadium = gf.Path()
    path_stadium.append(gf.path.straight(length=0.001))
    path_stadium.points = np.column_stack([x_coords, y_coords])

    # Extrude to create solid filled stadium
    # For a filled shape, use a very wide extrusion
    stadium_solid = c << path_stadium.extrude(width=stadium_width * 1.2, layer=layer)

    # Cut out rectangular gaps using boolean operations
    # 2 rows of 2 gaps each (4 total gaps visible in target)
    gap_y_top = gap_spacing_y / 2
    gap_y_bottom = -gap_spacing_y / 2

    gap_x_left = stadium_length/2 - gap_spacing_x/2 - gap_width/2
    gap_x_right = stadium_length/2 + gap_spacing_x/2 + gap_width/2

    # Top row gaps
    gap1 = c << gf.components.rectangle(size=(gap_width, gap_height), layer=layer)
    gap1.center = (gap_x_left, gap_y_top)

    gap2 = c << gf.components.rectangle(size=(gap_width, gap_height), layer=layer)
    gap2.center = (gap_x_right, gap_y_top)

    # Bottom row gaps
    gap3 = c << gf.components.rectangle(size=(gap_width, gap_height), layer=layer)
    gap3.center = (gap_x_left, gap_y_bottom)

    gap4 = c << gf.components.rectangle(size=(gap_width, gap_height), layer=layer)
    gap4.center = (gap_x_right, gap_y_bottom)

    # Use boolean to subtract gaps from solid
    result = gf.boolean(A=stadium_solid, B=[gap1, gap2, gap3, gap4], operation="A-B", layer=layer)
    c << result

    return c


if __name__ == "__main__":
    component = stadium_with_gaps()
    gds_path = "device.gds"
    component.write_gds(gds_path)
    print(f"Written to {gds_path}")
