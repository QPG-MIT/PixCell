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

    # Top thin curved lines (5 lines)
    n = 5
    base_top = 2.1
    delta_mid = 0.1
    delta_end = (4.0 - base_top) / (n - 1)
    for i in range(1, n + 1):
        y_mid = base_top + (i - 1) * delta_mid
        y_end = base_top + (i - 1) * delta_end
        points = arc_points(y_mid, y_end)
        path = gf.Path(points)
        line = gf.path.extrude(path, cross_section=xs_thin)
        c << line

    # Bottom thin curved lines (5 lines)
    base_bottom = 1.9
    for i in range(1, n + 1):
        y_mid = base_bottom - (i - 1) * delta_mid
        y_end = base_bottom - (i - 1) * delta_end
        points = arc_points(y_mid, y_end)
        path = gf.Path(points)
        line = gf.path.extrude(path, cross_section=xs_thin)
        c << line

    return c

# Create the device
dev = device()
dev.write_gds("device.gds")