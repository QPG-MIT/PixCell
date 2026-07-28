import json
import gdsfactory as gf

# Image-calibrated, intentionally top-level tunables.
wg_width = 0.068
delta_length = 1.0
track_pitch = 0.100
horizontal_span = 104.0
turn_radius = 3.0
bank_separation = 0.52
central_pitch = 0.078
layer = (1, 0)


def _rect(c, length, width, x, y):
    r = gf.components.rectangle(size=(length, width), layer=layer, centered=False)
    c.add_ref(r).move((x, y))


def _path(c, points, width=wg_width):
    p = gf.Path(points)
    c.add_ref(gf.path.extrude(p, width=width, layer=layer))


@gf.cell
def device():
    c = gf.Component("pixcell_final8_recreation")
    inner_x = 5.0 + turn_radius
    span = 120.0 - 2.0 * inner_x
    # Five isolated guides in the central band.
    central_y = [1.77 + i * central_pitch for i in range(5)]
    for y in central_y:
        _rect(c, 120.0, wg_width, 0.0, y)

    # Upper and lower repeated horizontal guides.
    upper_y = [0.766 + i * track_pitch for i in range(5)]
    lower_y = [2.77 + i * track_pitch for i in range(5)]
    for y in upper_y + lower_y:
        _rect(c, span, wg_width, inner_x, y)

    # The broad inner return regions visible in the raster.
    _rect(c, span, 0.47, inner_x, 1.264)
    _rect(c, span, 0.47, inner_x, 1.75 + bank_separation)

    # Paired vertical leads at both ends, extending beyond the calibrated crop.
    for x in (4.0, 6.2, 113.8, 116.0):
        _path(c, [(x, -0.55), (x, 0.77)], width=wg_width)
        _path(c, [(x, 3.23), (x, 4.55)], width=wg_width)

    # End transitions represented with path primitives.
    for y0, y1 in ((0.766, 1.264), (1.74, 1.75 + bank_separation), (2.74, 3.23)):
        _path(c, [(4.0, y0), (4.0, y1), (inner_x, y1)], width=wg_width)
        _path(c, [(116.0, y0), (116.0, y1), (120.0 - inner_x, y1)], width=wg_width)
    # Parametric delay extension, placed outside the calibrated image window.
    arm_ref = gf.Path([(0.0, 4.3), (1.0, 4.3)])
    delay_path = gf.Path([(0.0, 4.2), (1.0 + delta_length, 4.2)])
    c.add_ref(gf.path.extrude(arm_ref, width=wg_width, layer=layer))
    c.add_ref(gf.path.extrude(delay_path, width=wg_width, layer=layer))
    c.info["arms"] = {"reference": arm_ref.length(), "delay": delay_path.length()}
    c.info["delta_length_um"] = delay_path.length() - arm_ref.length()
    return c


if __name__ == "__main__":
    component = device()
    component = component.copy()
    component.flatten()
    component.write_gds("device.gds", with_metadata=False)
    with open("lengths.json", "w") as f:
        json.dump({"arms": component.info["arms"], "delta_length_um": component.info["delta_length_um"]}, f)
