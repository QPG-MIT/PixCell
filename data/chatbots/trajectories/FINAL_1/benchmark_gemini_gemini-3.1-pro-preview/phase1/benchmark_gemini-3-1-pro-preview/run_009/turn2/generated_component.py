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
    # Starts at x=0 with width 0.4um and tapers down to a sharp point over 24um
    taper = c << gf.components.taper(
        length=24.0,
        width1=0.4,
        width2=0.01,
        layer=layer
    )

    # ---------------------------------------------------------
    # 2. Parametric Path Construction for Outer Arms
    # ---------------------------------------------------------
    # Segment 1: Angled inward to maintain constant gap with the central taper
    x1 = np.linspace(0, 24.0, 50)
    y1 = np.linspace(0.31, 0.21, 50)  # Angles downwards!
    
    # Segment 2: Smooth S-Bend (Length = 10.0)
    # We use a Cubic Hermite spline to ensure perfect C1 continuity. 
    # It starts with the exact downward slope of Segment 1 and ends perfectly horizontal.
    x2 = np.linspace(24.0, 34.0, 50)
    t = (x2 - 24.0) / 10.0  # Normalized parameter [0, 1]
    
    y_start = 0.21
    y_end = 0.65
    dy_dx_start = (0.21 - 0.31) / 24.0       # Slope from Segment 1
    v0_scaled = dy_dx_start * 10.0           # Chain rule scaling (dx/dt)
    
    # Hermite basis functions
    h00 = 2*t**3 - 3*t**2 + 1
    h10 = t**3 - 2*t**2 + t
    h01 = -2*t**3 + 3*t**2
    
    # Spline equation
    y2 = y_start * h00 + v0_scaled * h10 + y_end * h01

    # Segment 3: Final Straight section (Length = 6.0)
    x3 = np.linspace(34.0, 40.0, 20)
    y3 = np.full_like(x3, 0.65)

    # Concatenate coordinates
    x = np.concatenate([x1, x2[1:], x3[1:]])
    y = np.concatenate([y1, y2[1:], y3[1:]])

    # Convert to standard gf.Path objects
    p_top = gf.Path(list(zip(x, y)))
    p_bot = gf.Path(list(zip(x, -y)))  # Mirror for bottom arm

    # ---------------------------------------------------------
    # 3. Path Extrusion with Width Transition
    # ---------------------------------------------------------
    # The arms expand from 0.1um to 0.4um adiabatically across the full length
    xs_narrow = gf.cross_section.cross_section(width=0.1, layer=layer)
    xs_wide = gf.cross_section.cross_section(width=0.4, layer=layer)
    
    trans = gf.path.transition(cross_section1=xs_narrow, cross_section2=xs_wide, width_type='sine')

    # Version-safe extrusion
    try:
        c << gf.path.extrude_transition(p_top, trans)
        c << gf.path.extrude_transition(p_bot, trans)
    except AttributeError:
        c << gf.path.extrude(p_top, cross_section=trans)
        c << gf.path.extrude(p_bot, cross_section=trans)

    # ---------------------------------------------------------
    # Footprint Verification:
    # Top arm ends at y = +0.65, width = 0.4. Max Top Y = 0.65 + 0.2 = 0.85
    # Bottom arm ends at y = -0.65, width = 0.4. Min Bot Y = -0.65 - 0.2 = -0.85
    # Total Height = 0.85 - (-0.85) = 1.70 µm
    # Total Length = 40.0 µm
    # ---------------------------------------------------------
    
    return c

if __name__ == "__main__":
    device = adiabatic_mode_converter()
    device.write_gds("adiabatic_mode_converter.gds")