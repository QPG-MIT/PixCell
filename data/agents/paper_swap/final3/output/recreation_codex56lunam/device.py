import json
from pathlib import Path

import gdsfactory as gf

# Function-defining, JEE-substitutable parameters (um).
wg_width = 0.28
bend_radius = 0.30
coupling_gap = 0.14
coupling_length = 78.80
port_separation = 3.60
access_length = 20.0
vertical_trim = 1.40

layer = (1, 0)


def _s_path(y_outer: float, y_inner: float, sign: float) -> gf.Path:
    """Build a horizontal-to-horizontal S access path with circular bends."""
    p = gf.Path()
    p.append(gf.path.straight(access_length))
    p.append(gf.path.arc(bend_radius, 90 * sign, start_angle=0))
    p.append(gf.path.straight(vertical_trim))
    p.append(gf.path.arc(bend_radius, -90 * sign, start_angle=90 * sign))
    p.append(gf.path.straight(coupling_length))
    p.append(gf.path.arc(bend_radius, -90 * sign, start_angle=0))
    p.append(gf.path.straight(vertical_trim))
    p.append(gf.path.arc(bend_radius, 90 * sign, start_angle=-90 * sign))
    p.append(gf.path.straight(access_length))
    # Path objects are centered by their convenience x/y setters; translate
    # from the actual first centerline point so ports land at the footprint
    # edges with the requested vertical coordinates.
    p.move(origin=tuple(p.points[0]), destination=(0, y_outer))
    return p


@gf.cell
def directional_coupler():
    c = gf.Component()
    center_sep = wg_width + coupling_gap
    # The top guide moves downward into the coupling region; the lower guide
    # moves upward. Their centerlines remain parallel over coupling_length.
    top = _s_path(port_separation, port_separation / 2 + center_sep / 2, -1)
    bottom = _s_path(0.0, port_separation / 2 - center_sep / 2, 1)
    c.add_ref(gf.path.extrude(top, layer=layer, width=wg_width))
    c.add_ref(gf.path.extrude(bottom, layer=layer, width=wg_width))
    def path_length(path):
        points = path.points
        return float((((points[1:] - points[:-1]) ** 2).sum(axis=1) ** 0.5).sum())

    top_length = path_length(top)
    bottom_length = path_length(bottom)
    Path(__file__).with_name("lengths.json").write_text(json.dumps({
        "arms": {"top": top_length, "bottom": bottom_length},
        "delta_length_um": abs(top_length - bottom_length),
    }, indent=2))
    return c


component = directional_coupler()
component.write_gds(Path(__file__).with_name("device.gds"))
