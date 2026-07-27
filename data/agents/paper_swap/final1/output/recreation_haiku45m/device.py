import gdsfactory as gf
import numpy as np

# Tunables
wg_width_um = 0.58
taper_width_min_um = 0.22
gap_um = 0.48
coupler_length_um = 17.0
taper_length_um = 7.5
total_length_um = 40.0

@gf.cell
def two_waveguide_directional_coupler():
    """
    Two-waveguide directional coupler with 3-segment tapers.
    Each taper is divided into 3 segments for smoother S-bends.
    """
    c = gf.Component()
    layer = (1, 0)

    central_length = 2 * taper_length_um + coupler_length_um
    remaining = total_length_um - central_length
    left_straight = remaining / 2.0
    right_straight = remaining - left_straight

    if left_straight <= 0.1:
        left_straight = 0.5
    if right_straight <= 0.1:
        right_straight = 0.5

    y_top = gap_um / 2
    y_bottom = -gap_um / 2

    # Helper: create tapered waveguide polygon with 3-segment approximation
    def make_3seg_taper(x_start, y_center, length, width_in, width_out):
        seg_len = length / 3
        w1_to_mid = width_in + (width_out - width_in) * 0.333
        w_mid_to_out = width_out + (width_in - width_out) * 0.333

        polys = []

        # Segment 1: width_in -> w1_to_mid
        half_w_in = width_in / 2
        half_w_mid = w1_to_mid / 2
        poly1 = np.array([
            [x_start, y_center - half_w_in],
            [x_start + seg_len, y_center - half_w_mid],
            [x_start + seg_len, y_center + half_w_mid],
            [x_start, y_center + half_w_in],
        ])
        polys.append(poly1)

        # Segment 2: w1_to_mid -> w_mid_to_out
        half_w_mid2 = w_mid_to_out / 2
        poly2 = np.array([
            [x_start + seg_len, y_center - half_w_mid],
            [x_start + 2*seg_len, y_center - half_w_mid2],
            [x_start + 2*seg_len, y_center + half_w_mid2],
            [x_start + seg_len, y_center + half_w_mid],
        ])
        polys.append(poly2)

        # Segment 3: w_mid_to_out -> width_out
        half_w_out = width_out / 2
        poly3 = np.array([
            [x_start + 2*seg_len, y_center - half_w_mid2],
            [x_start + length, y_center - half_w_out],
            [x_start + length, y_center + half_w_out],
            [x_start + 2*seg_len, y_center + half_w_mid2],
        ])
        polys.append(poly3)

        return polys

    def make_straight(x_start, y_center, length, width):
        half_w = width / 2
        return np.array([
            [x_start, y_center - half_w],
            [x_start + length, y_center - half_w],
            [x_start + length, y_center + half_w],
            [x_start, y_center + half_w],
        ])

    # ===== TOP WAVEGUIDE =====
    x_pos = 0

    # Left straight
    if left_straight > 0.1:
        poly = make_straight(x_pos, y_top, left_straight, wg_width_um)
        c.add_polygon(poly, layer=layer)
        x_pos += left_straight

    # Left taper (3 segments)
    for poly in make_3seg_taper(x_pos, y_top, taper_length_um, wg_width_um, taper_width_min_um):
        c.add_polygon(poly, layer=layer)
    x_pos += taper_length_um

    # Coupler
    poly = make_straight(x_pos, y_top, coupler_length_um, taper_width_min_um)
    c.add_polygon(poly, layer=layer)
    x_pos += coupler_length_um

    # Right taper (3 segments)
    for poly in make_3seg_taper(x_pos, y_top, taper_length_um, taper_width_min_um, wg_width_um):
        c.add_polygon(poly, layer=layer)
    x_pos += taper_length_um

    # Right straight
    if right_straight > 0.1:
        poly = make_straight(x_pos, y_top, right_straight, wg_width_um)
        c.add_polygon(poly, layer=layer)

    # ===== BOTTOM WAVEGUIDE =====
    x_pos = 0

    # Left straight
    if left_straight > 0.1:
        poly = make_straight(x_pos, y_bottom, left_straight, wg_width_um)
        c.add_polygon(poly, layer=layer)
        x_pos += left_straight

    # Left taper
    for poly in make_3seg_taper(x_pos, y_bottom, taper_length_um, wg_width_um, taper_width_min_um):
        c.add_polygon(poly, layer=layer)
    x_pos += taper_length_um

    # Coupler
    poly = make_straight(x_pos, y_bottom, coupler_length_um, taper_width_min_um)
    c.add_polygon(poly, layer=layer)
    x_pos += coupler_length_um

    # Right taper
    for poly in make_3seg_taper(x_pos, y_bottom, taper_length_um, taper_width_min_um, wg_width_um):
        c.add_polygon(poly, layer=layer)
    x_pos += taper_length_um

    # Right straight
    if right_straight > 0.1:
        poly = make_straight(x_pos, y_bottom, right_straight, wg_width_um)
        c.add_polygon(poly, layer=layer)

    return c

if __name__ == "__main__":
    c = two_waveguide_directional_coupler()
    c.write_gds("device.gds")
    print("GDS written to device.gds")
