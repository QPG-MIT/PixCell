import json
import gdsfactory as gf


# Geometry knobs (micrometres); kept as simple top-level assignments for HOMI.
layer = (1, 0)
wg_width = 0.30
outer_radius = 1.35
outer_side_length = 2.50
outer_x = 3.00
inner_separation = 1.75
delta_length = 0.10
inner_length = 2.05 + delta_length / 2
inner_width = 0.30
window_width = 0.34
window_height = 0.62
window_gap = 0.10
frame_bar = 0.30
frame_side = 0.12 + 0.02 * delta_length
transition = 0.42


def _rect(c, x, y, w, h):
    r = gf.components.rectangle(size=(w, h), layer=layer)
    c.add_ref(r).move((x, y))


def _path(c, points, width=wg_width):
    p = gf.Path()
    for kind, value in points:
        if kind == "straight":
            p += gf.path.straight(length=value)
        else:
            p += gf.path.arc(radius=value[0], angle=value[1])
    c.add_ref(gf.path.extrude(p, width=width, layer=layer))


@gf.cell
def device():
    c = gf.Component("pixcell_final7")

    # Closed outer racetrack, starting at the lower-left side and travelling up.
    # The two semicircles provide smooth side turns while the straight portions
    # establish the long top and bottom runs visible in the reference.
    p = gf.Path()
    p += gf.path.straight(length=outer_side_length)
    p += gf.path.arc(radius=outer_radius, angle=180)
    p += gf.path.straight(length=outer_side_length)
    p += gf.path.arc(radius=outer_radius, angle=180)
    ref = c.add_ref(gf.path.extrude(p, width=wg_width, layer=layer))
    ref.move((-outer_side_length / 2, -outer_radius))
    ref.rotate(90)

    frame_w = 2 * window_width + window_gap + 2 * frame_side
    frame_h = window_height + 2 * frame_side

    # Inner pair of parallel guides, with the short diagonal lead-ins that
    # connect visually to the outer loop at each end.
    for y in (-inner_separation / 2, inner_separation / 2):
        _rect(c, -inner_length / 2, y - inner_width / 2, inner_length / 2 - frame_w / 2, inner_width)
        _rect(c, frame_w / 2, y - inner_width / 2, inner_length / 2 - frame_w / 2, inner_width)
        _rect(c, -outer_x / 2 + 0.18, y - inner_width / 2, 0.55, inner_width)
        _rect(c, outer_x / 2 - 0.73, y - inner_width / 2, 0.55, inner_width)

    # Two framed central clearances, one around each inner guide.  The frame is
    # explicitly assembled from primitive rectangles so the white windows are
    # true open regions rather than a pre-built device stencil.
    for y in (-inner_separation / 2, inner_separation / 2):
        x0 = -frame_w / 2
        y0 = y - frame_h / 2
        _rect(c, x0, y0, frame_w, frame_bar)
        _rect(c, x0, y0 + frame_h - frame_bar, frame_w, frame_bar)
        _rect(c, x0, y0, frame_side, frame_h)
        _rect(c, x0 + frame_w - frame_side, y0, frame_side, frame_h)
        _rect(c, -window_gap / 2 - frame_bar / 2, y0, frame_bar, frame_h)

    return c


if __name__ == "__main__":
    component = device().copy()
    component.flatten()
    component.write_gds("device.gds")
    with open("lengths.json", "w") as f:
        json.dump({"arms": {"upper": inner_length, "lower": inner_length + delta_length},
                   "delta_length_um": delta_length}, f)
