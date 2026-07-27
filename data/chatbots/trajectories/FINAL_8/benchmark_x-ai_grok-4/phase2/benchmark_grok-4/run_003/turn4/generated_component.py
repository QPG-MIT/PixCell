import gdsfactory as gf

@gf.cell
def curved_wg(x_span=120.0, y_center=0.0, dy=0.0, cross_section=None):
    x_end = x_span / 2
    p1 = (-x_end, y_center + dy)
    p2 = (0, y_center)
    p3 = (x_end, y_center + dy)

    # Implement quadratic Bezier curve sampling
    npoints = 101
    points = []
    for i in range(npoints):
        t = i / (npoints - 1)
        x = (1 - t)**2 * p1[0] + 2 * (1 - t) * t * p2[0] + t**2 * p3[0]
        y = (1 - t)**2 * p1[1] + 2 * (1 - t) * t * p2[1] + t**2 * p3[1]
        points.append((x, y))

    path = gf.Path(points)
    return gf.path.extrude(path, cross_section=cross_section)

@gf.cell
def the_device():
    c = gf.Component()
    xs_thin = gf.cross_section.cross_section(width=0.2, layer=(1, 0))

    # Top thin lines (outer to inner)
    top_y = [1.9, 1.6, 1.3, 1.0]
    top_dy = [0.1, 0.4, 0.7, 1.0]
    for y, d in zip(top_y, top_dy):
        c << curved_wg(y_center=y, dy=d, cross_section=xs_thin)

    # Bottom thin lines (outer to inner)
    bottom_y = [-1.9, -1.6, -1.3, -1.0]
    bottom_dy = [-0.1, -0.4, -0.7, -1.0]
    for y, d in zip(bottom_y, bottom_dy):
        c << curved_wg(y_center=y, dy=d, cross_section=xs_thin)

    # Central solid
    ell = gf.components.ellipse(radii=(60, 1.0), layer=(1, 0))
    c << ell

    return c

device = the_device()
device.write_gds("my_device.gds")