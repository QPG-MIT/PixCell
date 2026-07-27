import gdsfactory as gf
import numpy as np

@gf.cell
def adiabatic_mode_converter():
    """
    Parametric reconstruction of the spot-size converter device.
    Uses calculated parametric polygons to ensure perfect, artifact-free 
    C1 continuous transitions that exactly hit the target constraints.
    Footprint constraint: [40.0, 1.7] (Width x Height)
    """
    c = gf.Component("adiabatic_mode_converter")
    layer = (1, 0)

    # ---------------------------------------------------------
    # 1. Central Taper 
    # ---------------------------------------------------------
    # Starts at x=0, tapering to a sharp point at x=25.0
    c << gf.components.taper(
        length=25.0,
        width1=0.4,
        width2=0.002, 
        layer=layer
    )

    # ---------------------------------------------------------
    # 2. Outer Arms Generation (Mathematical Boundary Tracing)
    # ---------------------------------------------------------
    # We use a high density of points to guarantee a perfectly smooth curvature
    x_pts = np.linspace(3.0, 40.0, 1000)
    y_c = np.zeros_like(x_pts)
    dy_dx = np.zeros_like(x_pts)
    width = np.zeros_like(x_pts)

    m1 = x_pts <= 25.0                           # Hugging Region
    m2 = (x_pts > 25.0) & (x_pts <= 35.0)        # S-Bend Transition Region
    m3 = x_pts > 35.0                            # Output Region

    # --- Region 1: Hugging the taper ---
    # Taper top edge equation: y = 0.2 - x * (0.2 - 0.001) / 25.0
    slope = -0.00796
    
    # We want a rigid 0.05um gap from the taper edge
    # Inner edge = y_taper + 0.05 = 0.25 + slope * x
    # Centerline = Inner edge + width/2 = 0.25 + slope * x + 0.075
    y_c[m1] = 0.325 + slope * x_pts[m1]
    dy_dx[m1] = slope
    width[m1] = 0.15

    # --- Region 2: Hermite S-Bend & Cosine Width Transition ---
    t = (x_pts[m2] - 25.0) / 10.0
    y_start = 0.325 + slope * 25.0  # Exactly 0.126
    y_end = 0.65                    # Aligns perfectly with 1.7 total height constraint
    v0 = slope * 10.0               # Lock incoming tangent (dy/dt = dy/dx * dx/dt)
    v1 = 0.0                        # Exit perfectly horizontal

    # Hermite spline basis functions
    h00 = 2*t**3 - 3*t**2 + 1
    h10 = t**3 - 2*t**2 + t
    h01 = -2*t**3 + 3*t**2
    h11 = t**3 - t**2

    y_c[m2] = y_start * h00 + v0 * h10 + y_end * h01 + v1 * h11

    # Derivatives for exact normal calculation
    dh00 = 6*t**2 - 6*t
    dh10 = 3*t**2 - 4*t + 1
    dh01 = -6*t**2 + 6*t
    dh11 = 3*t**2 - 2*t

    dy_dt = y_start * dh00 + v0 * dh10 + y_end * dh01 + v1 * dh11
    dy_dx[m2] = dy_dt / 10.0

    # Sine (raised cosine) width transition
    width[m2] = 0.15 + (0.4 - 0.15) * (1 - np.cos(np.pi * t)) / 2

    # --- Region 3: Straight Out ---
    y_c[m3] = 0.65
    dy_dx[m3] = 0.0
    width[m3] = 0.4

    # ---------------------------------------------------------
    # Polygon Assembly via Exact Normal Offsetting
    # ---------------------------------------------------------
    # Tangent vector is (1, dy_dx). Unnormalized Normal is (-dy_dx, 1)
    Nx = -dy_dx
    Ny = 1.0
    norm = np.sqrt(Nx**2 + Ny**2)
    nx = Nx / norm
    ny = Ny / norm

    x_outer = x_pts + nx * width / 2
    y_outer = y_c + ny * width / 2
    x_inner = x_pts - nx * width / 2
    y_inner = y_c - ny * width / 2

    # Force perfectly vertical facets at the start and end
    x_outer[0], x_inner[0] = x_pts[0], x_pts[0]
    x_outer[-1], x_inner[-1] = x_pts[-1], x_pts[-1]

    # Combine traces to form the closed top arm
    pts_top = np.column_stack((x_outer, y_outer)).tolist() + \
              np.column_stack((x_inner[::-1], y_inner[::-1])).tolist()
    c.add_polygon(pts_top, layer=layer)

    # Combine traces for mirrored bottom arm
    pts_bot = np.column_stack((x_outer, -y_outer)).tolist() + \
              np.column_stack((x_inner[::-1], -y_inner[::-1])).tolist()
    c.add_polygon(pts_bot, layer=layer)

    return c


if __name__ == "__main__":
    device = adiabatic_mode_converter()
    device.write_gds("adiabatic_mode_converter.gds")