import gdsfactory as gf

@gf.cell
def my_device():
    c = gf.Component()
    w = 0.5
    r = 1.25
    s = 1.15
    gap = 0.2
    xs = gf.cross_section.cross_section(width=w, layer=(1, 0))

    # Build the U shape for right
    p = gf.Path()
    p.append(gf.path.straight(length=s))
    p.append(gf.path.arc(radius=r, angle=180))
    p.append(gf.path.straight(length=s))
    u = p.extrude(xs)

    # Add to c
    right_ref = c << u
    right_ref.move((gap / 2, -r))

    # For left
    left_ref = c << u
    left_ref.mirror()
    left_ref.move((-gap / 2, -r))

    return c

device = my_device()
device.write_gds("my_device.gds")