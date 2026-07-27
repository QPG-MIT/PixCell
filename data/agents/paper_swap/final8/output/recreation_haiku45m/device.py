import gdsfactory as gf
import numpy as np

# Parametric tunable knobs
wg_width_um = 0.5
n_guides = 5


@gf.cell
def adiabatic_coupler_v4():
    """
    Adiabatic tapered coupler (iteration 4: best so far at 0.215 IoU).

    Top taper (U-curves + interior guides) -> Central array -> Bottom taper
    """

    c = gf.Component()

    total_width = 120.0
    total_height = 4.0
    y_center = 0

    # Y-positions
    y_top = 1.8
    y_taper_top = 0.8  # Where taper transitions to array
    y_taper_bot = -0.8
    y_bot = -1.8

    # X-positions for the 5 guides
    x_guides = np.linspace(15, total_width - 15, n_guides)

    # === TOP TAPER SECTION ===

    # Left U-curve (input)
    pts_top_left = [
        (x_guides[0], y_top),
        (x_guides[0] - 8, y_top - 0.3),
        (x_guides[0] - 8, y_taper_top + 0.2),
        (x_guides[0], y_taper_top),
    ]
    path_top_left = gf.Path(pts_top_left)
    c << gf.path.extrude(path_top_left, width=wg_width_um, layer=(1, 0))

    # Right U-curve (input)
    pts_top_right = [
        (x_guides[-1], y_top),
        (x_guides[-1] + 8, y_top - 0.3),
        (x_guides[-1] + 8, y_taper_top + 0.2),
        (x_guides[-1], y_taper_top),
    ]
    path_top_right = gf.Path(pts_top_right)
    c << gf.path.extrude(path_top_right, width=wg_width_um, layer=(1, 0))

    # Interior guides in taper region
    for i in range(1, n_guides - 1):
        x_pos = x_guides[i]
        pts_interior = [
            (x_pos, y_top - 0.15),
            (x_pos, y_taper_top)
        ]
        path_interior = gf.Path(pts_interior)
        c << gf.path.extrude(path_interior, width=wg_width_um, layer=(1, 0))

    # === CENTRAL COUPLING ARRAY ===
    for x_pos in x_guides:
        path_central = gf.Path([
            (x_pos, y_taper_top),
            (x_pos, y_taper_bot)
        ])
        c << gf.path.extrude(path_central, width=wg_width_um, layer=(1, 0))

    # === BOTTOM TAPER (mirror of top) ===

    # Interior guides in bottom taper
    for i in range(1, n_guides - 1):
        x_pos = x_guides[i]
        pts_interior_bot = [
            (x_pos, y_taper_bot),
            (x_pos, y_bot + 0.15)
        ]
        path_interior_bot = gf.Path(pts_interior_bot)
        c << gf.path.extrude(path_interior_bot, width=wg_width_um, layer=(1, 0))

    # Left U-curve (output)
    pts_bot_left = [
        (x_guides[0], y_taper_bot),
        (x_guides[0] - 8, y_taper_bot - 0.2),
        (x_guides[0] - 8, y_bot + 0.3),
        (x_guides[0], y_bot),
    ]
    path_bot_left = gf.Path(pts_bot_left)
    c << gf.path.extrude(path_bot_left, width=wg_width_um, layer=(1, 0))

    # Right U-curve (output)
    pts_bot_right = [
        (x_guides[-1], y_taper_bot),
        (x_guides[-1] + 8, y_taper_bot - 0.2),
        (x_guides[-1] + 8, y_bot + 0.3),
        (x_guides[-1], y_bot),
    ]
    path_bot_right = gf.Path(pts_bot_right)
    c << gf.path.extrude(path_bot_right, width=wg_width_um, layer=(1, 0))

    return c


if __name__ == "__main__":
    component = adiabatic_coupler_v4()
    component.write_gds("device.gds")
    print("Device written to device.gds")
