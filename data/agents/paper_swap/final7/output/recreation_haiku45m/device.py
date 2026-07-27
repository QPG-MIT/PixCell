import gdsfactory as gf
import numpy as np

# Parametric tunables — Iteration 1 best (IoU = 0.254)
straight_width_um = 0.5
ring_radius_um = 1.2
coupler_gap_um = 0.3
cavity_width_um = 0.25
cavity_height_um = 0.6
cavity_offset_y_um = 1.5

@gf.cell
def device(
    straight_width=straight_width_um,
    ring_radius=ring_radius_um,
    coupler_gap=coupler_gap_um,
    cavity_width=cavity_width_um,
    cavity_height=cavity_height_um,
    cavity_offset_y=cavity_offset_y_um,
):
    c = gf.Component()

    # Bottom waveguide
    bottom_y = -coupler_gap / 2 - straight_width / 2
    c.add_polygon([
        [-ring_radius - 0.5, bottom_y - straight_width / 2],
        [ring_radius + 0.5, bottom_y - straight_width / 2],
        [ring_radius + 0.5, bottom_y + straight_width / 2],
        [-ring_radius - 0.5, bottom_y + straight_width / 2],
    ], layer=(1, 0))

    # Top waveguide
    top_y = coupler_gap / 2 + straight_width / 2
    c.add_polygon([
        [-ring_radius - 0.5, top_y - straight_width / 2],
        [ring_radius + 0.5, top_y - straight_width / 2],
        [ring_radius + 0.5, top_y + straight_width / 2],
        [-ring_radius - 0.5, top_y + straight_width / 2],
    ], layer=(1, 0))

    # Ring: right semicircle
    right_arc_outer = [[ring_radius * np.cos(np.radians(a)), ring_radius * np.sin(np.radians(a))]
                       for a in np.linspace(-90, 90, 50)]
    right_arc_inner = [[(ring_radius - straight_width) * np.cos(np.radians(a)),
                        (ring_radius - straight_width) * np.sin(np.radians(a))]
                       for a in np.linspace(90, -90, 50)]
    right_arc = right_arc_outer + right_arc_inner
    c.add_polygon(right_arc, layer=(1, 0))

    # Ring: left semicircle
    left_arc_outer = [[ring_radius * np.cos(np.radians(a)), ring_radius * np.sin(np.radians(a))]
                      for a in np.linspace(90, 270, 50)]
    left_arc_inner = [[(ring_radius - straight_width) * np.cos(np.radians(a)),
                       (ring_radius - straight_width) * np.sin(np.radians(a))]
                      for a in np.linspace(270, 90, 50)]
    left_arc = left_arc_outer + left_arc_inner
    c.add_polygon(left_arc, layer=(1, 0))

    # Cavity rectangles
    # Top-left cavity
    cav_tl_x = -cavity_width / 2 - cavity_width / 2 - 0.1
    cav_tl_y = cavity_offset_y
    cav_tl_pts = [
        [cav_tl_x - cavity_width / 2, cav_tl_y - cavity_height / 2],
        [cav_tl_x + cavity_width / 2, cav_tl_y - cavity_height / 2],
        [cav_tl_x + cavity_width / 2, cav_tl_y + cavity_height / 2],
        [cav_tl_x - cavity_width / 2, cav_tl_y + cavity_height / 2],
    ]
    c.add_polygon(cav_tl_pts, layer=(1, 0))

    # Top-right cavity
    cav_tr_x = cavity_width / 2 + cavity_width / 2 + 0.1
    cav_tr_y = cavity_offset_y
    cav_tr_pts = [
        [cav_tr_x - cavity_width / 2, cav_tr_y - cavity_height / 2],
        [cav_tr_x + cavity_width / 2, cav_tr_y - cavity_height / 2],
        [cav_tr_x + cavity_width / 2, cav_tr_y + cavity_height / 2],
        [cav_tr_x - cavity_width / 2, cav_tr_y + cavity_height / 2],
    ]
    c.add_polygon(cav_tr_pts, layer=(1, 0))

    # Bottom-left cavity
    cav_bl_x = -cavity_width / 2 - cavity_width / 2 - 0.1
    cav_bl_y = -cavity_offset_y
    cav_bl_pts = [
        [cav_bl_x - cavity_width / 2, cav_bl_y - cavity_height / 2],
        [cav_bl_x + cavity_width / 2, cav_bl_y - cavity_height / 2],
        [cav_bl_x + cavity_width / 2, cav_bl_y + cavity_height / 2],
        [cav_bl_x - cavity_width / 2, cav_bl_y + cavity_height / 2],
    ]
    c.add_polygon(cav_bl_pts, layer=(1, 0))

    # Bottom-right cavity
    cav_br_x = cavity_width / 2 + cavity_width / 2 + 0.1
    cav_br_y = -cavity_offset_y
    cav_br_pts = [
        [cav_br_x - cavity_width / 2, cav_br_y - cavity_height / 2],
        [cav_br_x + cavity_width / 2, cav_br_y - cavity_height / 2],
        [cav_br_x + cavity_width / 2, cav_br_y + cavity_height / 2],
        [cav_br_x - cavity_width / 2, cav_br_y + cavity_height / 2],
    ]
    c.add_polygon(cav_br_pts, layer=(1, 0))

    return c

if __name__ == "__main__":
    c = device()
    c.show()
    import os
    os.chdir('/Users/aadarwal/src/QPG-MIT/homi-anu-powered/experiments/paper_swap/final7/output/recreation_haiku45m')
    c.write_gds('device.gds')
    print("GDS written to device.gds")
