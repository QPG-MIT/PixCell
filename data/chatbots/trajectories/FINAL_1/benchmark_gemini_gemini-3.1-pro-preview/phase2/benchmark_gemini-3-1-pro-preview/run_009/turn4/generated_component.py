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
    # Slope of edge = (0.001 - 0.2) / 25 = -0.00796
    c << gf.components.taper(
        length=25.0,
        width1=0.4,
        width2=0.002, 
        layer=layer
    )

    # ---------------------------------------------------------
    # 2. Outer Arms Setup & Cross Sections
    # ---------------------------------------------------------
    w_narrow = 0.15
    w_wide = 0.4
    
    xs_hugging = gf.cross_section.cross_section(width=w_narrow, layer=layer)
    xs_wide = gf.cross_section.cross_section(width=w_wide, layer=layer)
    trans_sbend = gf.path.transition(
        cross_section1=xs_hugging, 
        cross_section2=xs_wide, 
        width_type='sine'
    )

    # ---------------------------------------------------------
    # Segment A: Hugging Section (Straight, constant width)
    # ---------------------------------------------------------
    # We maintain a strict 0.05um gap parallel to the taper.
    # y_inner = y_taper_edge + 0.05
    # y_center = y_inner + w_narrow/2 
    # Precomputed y_centers to guarantee perfect linearity:
    y_c_start = 0.30112  # At x=3.0
    y_c_end = 0.126      # At x=25.0
    slope = -0.00796
    
    pA_top = gf.Path([(3.0, y_c_start), (25.0, y_c_end)])
    pA_bot = gf.Path([(3.0, -y_c_start), (25.0, -y_c_end)])
    
    c << gf.path.extrude(pA_top, cross_section=xs_hugging)
    c << gf.path.extrude(pA_bot, cross_section=xs_hugging)

    # ---------------------------------------------------------
    # Segment B: S-Bend Section (Curved, widening transition)
    # ---------------------------------------------------------
    x_B = np.linspace(25.0, 35.0, 60)
    t_B = (x_B - 25.0) / 10.0
    
    # Hermite spline for mathematically perfect C1 continuity
    y_start = y_c_end
    y_end = 0.65
    v0 = slope * 10.0  # Match incoming tangent exactly
    v1 = 0.0           # Exit perfectly flat
    
    h00 = 2*t_B**3 - 3*t_B**2 + 1
    h10 = t_B**3 - 2*t_B**2 + t_B
    h01 = -2*t_B**3 + 3*t_B**2
    h11 = t_B**3 - t_B**2
    
    y_B = y_start * h00 + v0 * h10 + y_end * h01 + v1 * h11
    
    pB_top = gf.Path(list(zip(x_B, y_B)))
    pB_bot = gf.Path(list(zip(x_B, -y_B)))

    # Version-safe transition extrusion
    try:
        c << gf.path.extrude_transition(pB_top, trans_sbend)
        c << gf.path.extrude_transition(pB_bot, trans_sbend)
    except AttributeError:
        c << gf.path.extrude(pB_top, cross_section=trans_sbend)
        c << gf.path.extrude(pB_bot, cross_section=trans_sbend)

    # ---------------------------------------------------------
    # Segment C: Straight Output Section
    # ---------------------------------------------------------
    pC_top = gf.Path([(35.0, 0.65), (40.0, 0.65)])
    pC_bot = gf.Path([(35.0, -0.65), (40.0, -0.65)])
    
    c << gf.path.extrude(pC_top, cross_section=xs_wide)
    c << gf.path.extrude(pC_bot, cross_section=xs_wide)

    return c

if __name__ == "__main__":
    device = adiabatic_mode_converter()
    device.write_gds("adiabatic_mode_converter.gds")