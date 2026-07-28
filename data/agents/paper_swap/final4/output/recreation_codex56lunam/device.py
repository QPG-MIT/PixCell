import math
import json
import gdsfactory as gf


# Function-defining, top-level tunables (micrometres).
wg_width = 0.65
min_gap = 0.30
interaction_length = 2.0
transition_length = 8.0
end_center_spacing = 2.35
footprint_length = 18.0
layer = (1, 0)


@gf.cell
def coupler(
    width: float = wg_width,
    gap: float = min_gap,
    interaction: float = interaction_length,
    transition: float = transition_length,
    end_spacing: float = end_center_spacing,
):
    """Symmetric two-rail adiabatic/directional coupler from smooth paths."""
    total_length = footprint_length
    center_spacing = width + gap
    y_end = end_spacing / 2
    y_center = center_spacing / 2
    x0 = 0.0
    x1 = x0 + transition
    x2 = x0 + transition + interaction
    x3 = x0 + total_length

    def eased_points(sign: float):
        points = []
        samples = 40
        for i in range(samples + 1):
            u = i / samples
            x = x0 + (x1 - x0) * u
            y = y_center + (y_end - y_center) * 0.5 * (1 + math.cos(math.pi * u))
            points.append((x, sign * y))
        points.append((x2, sign * y_center))
        for i in range(1, samples + 1):
            u = i / samples
            x = x2 + (x3 - x2) * u
            y = y_center + (y_end - y_center) * 0.5 * (1 - math.cos(math.pi * u))
            points.append((x, sign * y))
        return points

    upper_path = gf.Path(eased_points(1.0))
    lower_path = gf.Path(eased_points(-1.0))
    upper = gf.path.extrude(upper_path, width=width, layer=layer)
    lower = gf.path.extrude(lower_path, width=width, layer=layer)

    c = gf.Component()
    c.add_ref(upper)
    c.add_ref(lower)
    upper_length = upper_path.length()
    lower_length = lower_path.length()
    with open("lengths.json", "w", encoding="utf-8") as f:
        json.dump(
            {
                "arms": {"upper": upper_length, "lower": lower_length},
                "delta_length_um": abs(upper_length - lower_length),
            },
            f,
            indent=2,
        )
    return c


component = coupler()
component.write_gds("device.gds")
