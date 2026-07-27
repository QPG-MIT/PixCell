import gdsfactory as gf
import numpy as np

@gf.cell
def adiabatic_mode_converter():
    """
    Parametric reconstruction of the spot-size converter device.
    Footprint constraint: [40.0, 1.7] (Width x Height)
    """
    c = gf.Component("adiabatic_mode_converter")
    layer = (1, 0)

    # ---------------------------------------------------------
    # 1. Central Taper 
    # ---------------------------------------------------------
    # Starts at x=0, tapering to a sharp point at x=25.0
    taper = c << gf.components.taper(
        length=25.0,
        width1=0.4,
        width2=0.002,  # Sharp tip
        layer=layer
    )

    # ---------------------------------------------------------
    # 2. Parametric Path Construction for Outer Arms
    # ---------------------------------------------------------
    # The arms start at x=3.0, creating the offset seen in the target image.
    # We calculate the path centers to maintain a ~0.05um gap with the central 
    # taper, explicitly accounting for the 'sine' width transition.
    
    # Segment 1: Angled inward to hug the taper (x = 3.0 to 25.0)
    x1 = np.linspace(3.0, 25.0, 50)
    # y-coordinates are fine-tuned. At x=25, the sine transition reaches ~0.294um width.
    # To leave a 0.05um gap from y=0, the center must be at y=0.197.
    y1 = np.linspace(0.276, 0.197, 50)  
    
    # Segment 2: Smooth S-Bend sweeping outwards (x = 25.0 to 34.0)
    x2 = np.linspace(25.0, 34.0, 60)
    t = (x2 - 25.0) / 9.0 
    
    y_start = 0.197
    y_end = 0.65
    dy_dx_start = (0.197 - 0.276) / 22.0  # C1 Continuity: Match incoming slope
    v0_scaled = dy_dx_start * 9.0
    
    # Hermite spline basis functions for a mathematically perfect smooth curve
    h00 = 2*t**3 - 3*t**2 + 1
    h10 = t**3 - 2*t**2 + t
    h01 = -2*t**3 + 3*t**2
    
    y2 = y_start * h00 + v0_scaled * h10 + y_end * h01

    # Segment 3: Final Straight routing section (x = 34.0 to 40.0)
    x3 = np.linspace(34.0, 40.0, 20)
    y3 = np.full_like(x3, 0.65)

    # Concatenate coordinates and build symmetrical paths
    x = np.concatenate([x1, x2[1:], x3[1:]])
    y = np.concatenate([y1, y2[1:], y3[1:]])

    p_top = gf.Path(list(zip(x, y)))
    p_bot = gf.Path(list(zip(x, -y)))

    # ---------------------------------------------------------
    # 3. Path Extrusion with Width Transition
    # ---------------------------------------------------------
    # Outer arms smoothly transition from thin to thick
    xs_narrow = gf.cross_section.cross_section(width=0.1, layer=layer)
    xs_wide = gf.cross_section.cross_section(width=0.4, layer=layer)
    
    trans = gf.path.transition(
        cross_section1=xs_narrow, 
        cross_section2=xs_wide, 
        width_type='sine'
    )

    # Version-safe extrusion
    try:
        c << gf.path.extrude_transition(p_top, trans)
        c << gf.path.extrude_transition(p_bot, trans)
    except AttributeError:
        c << gf.path.extrude(p_top, cross_section=trans)
        c << gf.path.extrude(p_bot, cross_section=trans)

    # ---------------------------------------------------------
    # Footprint Verification:
    # Max Top Edge = 0.65 (center) + 0.2 (half-width) = 0.85
    # Min Bot Edge = -0.65 (center) - 0.2 (half-width) = -0.85
    # Total Height = 0.85 - (-0.85) = 1.70 µm  [Target met]
    # Total Length = 40.0 µm [Target met]
    # ---------------------------------------------------------

    return c

if __name__ == "__main__":
    device = adiabatic_mode_converter()
    device.write_gds("adiabatic_mode_converter.gds")