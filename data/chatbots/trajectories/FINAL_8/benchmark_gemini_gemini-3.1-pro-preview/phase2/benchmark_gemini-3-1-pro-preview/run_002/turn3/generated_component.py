import gdsfactory as gf
import numpy as np
from gdsfactory.cross_section import Section, cross_section

@gf.cell
def multi_slot_coupler() -> gf.Component:
    c = gf.Component()

    # --- Design Proportions & Constraints ---
    # Scaled to fit perfectly within the [120.0, 4.0] footprint
    w_thin = 0.06
    w_thick = 0.5
    pitch = 0.12
    gap_thick = 0.10  # Gap between top thin line and the thick boundary line

    # --- 1. Center Straight Group ---
    # 5 distinct thin lines straight through the middle
    # Offsets: -0.24, -0.12, 0, 0.12, 0.24
    xs_center = cross_section(
        width=w_thin, 
        offset=0, 
        layer=(1, 0),
        sections=[
            Section(width=w_thin, offset=-2*pitch, layer=(1, 0)),
            Section(width=w_thin, offset=-pitch, layer=(1, 0)),
            Section(width=w_thin, offset=pitch, layer=(1, 0)),
            Section(width=w_thin, offset=2*pitch, layer=(1, 0)),
        ]
    )
    
    path_center = gf.Path([(-60, 0), (60, 0)])
    c << gf.path.extrude(path_center, cross_section=xs_center)

    # --- 2. Top Flared Group ---
    # y_mid is chosen to perfectly continue the grating pitch from the center group
    # (Center group max is 0.24, so next line should be at 0.36)
    y_mid = 0.36
    y_out = 1.0  # Outer Y coordinate where the S-bend terminates
    
    # Calculate offset for the thick line relative to the base of the top group
    # Highest thin line is at offset: 3 * pitch = 0.36
    # Top edge of highest thin line = 0.36 + (0.06/2) = 0.39
    # Center of thick line = 0.39 + gap_thick + (0.5/2) = 0.74
    thick_offset = 0.74

    xs_top = cross_section(
        width=w_thick, 
        offset=thick_offset, 
        layer=(1, 0),
        sections=[
            Section(width=w_thin, offset=0.0, layer=(1, 0)),
            Section(width=w_thin, offset=pitch, layer=(1, 0)),
            Section(width=w_thin, offset=2*pitch, layer=(1, 0)),
            Section(width=w_thin, offset=3*pitch, layer=(1, 0)),
        ]
    )

    # Parametric Smooth S-Bend Master Path
    # Using cosine interpolation for C1/C2 continuity at both ends
    x_left = np.linspace(-60, -20, 100)
    t_left = (x_left - (-60)) / 40.0
    y_left = y_out - (y_out - y_mid) * (1 - np.cos(t_left * np.pi)) / 2

    x_mid = np.linspace(-20, 20, 10)
    y_mid_arr = np.full_like(x_mid, y_mid)

    x_right = np.linspace(20, 60, 100)
    t_right = (x_right - 20) / 40.0
    y_right = y_mid + (y_out - y_mid) * (1 - np.cos(t_right * np.pi)) / 2 

    # Concatenate safely removing duplicate overlapping bounds
    x_pts = np.concatenate([x_left, x_mid[1:-1], x_right])
    y_pts = np.concatenate([y_left, y_mid_arr[1:-1], y_right])
    
    path_top = gf.Path(list(zip(x_pts, y_pts)))
    
    # Extrude Top Group
    top_comp = c << gf.path.extrude(path_top, cross_section=xs_top)

    # --- 3. Bottom Flared Group ---
    # Extrude bottom from the exact same definitions and mirror it across X-axis
    bottom_comp = c << gf.path.extrude(path_top, cross_section=xs_top)
    bottom_comp.mirror(p1=(0, 0), p2=(1, 0))

    return c

if __name__ == "__main__":
    device = multi_slot_coupler()
    device.write_gds("multi_slot_coupler.gds")