import gdsfactory as gf
import numpy as np

def arc_points(y_mid, y_end, chord=120.0, npoints=101):
    if abs(y_mid - y_end) < 1e-3:
        x = np.linspace(0, chord, npoints)
        y = np.full(npoints, y_mid)
        return list(zip(x, y))
    s = abs(y_end - y_mid)
    r = ((chord / 2)**2 + s**2) / (2 * s)
    center_x = chord / 2
    if y_mid < y_end:
        center_y = y_mid + r
    else:
        center_y = y_mid - r
    start_angle = np.arctan2(y_end - center_y, 0 - center_x)
    end_angle = np.arctan2(y_end - center_y, chord - center_x)
    t = np.linspace(0, 1, npoints)
    angle = start_angle + t * (end_angle - start_angle)
    x = center_x + r * np.cos(angle)
    y = center_y + r * np.sin(angle)
    points = list(zip(x, y))
    # Reverse if x not increasing
    if x[0] > x[-1]:
        points = points[::-1]
    return points

@gf.cell
def device():
    c = gf.Component()

    # Define layer
    layer = (1, 0)

    # Define cross sections
    width_thin = 0.2
    xs_thin = gf.cross_section.cross_section(width=width_thin, layer=layer)

    width_thick = 0.8
    xs_thick = gf.cross_section.cross_section(width=width_thick, layer=layer)

    # Central thick straight (approximately, with slight curve for flare)
    y_mid_c = 2.0
    y_end_c = 2.1  # Slight flare
    points_c = arc_points(y_mid_c, y_end_c)
    path_c = gf.Path(points_c)
    central = gf.path.extrude(path_c, cross_section=xs_thick)
    c << central

    # Top thin curved lines (4 lines)
    n = 4
    y_mid_base_top = 2.0 + width_thick / 2 + width_thin / 2
    delta_mid = 0.5
    delta_end = 0.1
    for i in range(1, n + 1):
        y_mid = y_mid_base_top + (i - 1) * delta_mid
        y_end = y_mid_base_top + (i - 1) * delta_end
        points = arc_points(y_mid, y_end)
        path = gf.Path(points)
        line = gf.path.extrude(path, cross_section=xs_thin)
        c << line

    # Bottom thin curved lines (4 lines)
    y_mid_base_bottom = 2.0 - width_thick / 2 - width_thin / 2
    for i in range(1, n + 1):
        y_mid = y_mid_base_bottom - (i - 1) * delta_mid
        y_end = y_mid_base_bottom - (i - 1) * delta_end
        points = arc_points(y_mid, y_end)
        path = gf.Path(points)
        line = gf.path.extrude(path, cross_section=xs_thin)
        c << line

    return c

# Create the device
dev = device()
dev.write_gds("device.gds")