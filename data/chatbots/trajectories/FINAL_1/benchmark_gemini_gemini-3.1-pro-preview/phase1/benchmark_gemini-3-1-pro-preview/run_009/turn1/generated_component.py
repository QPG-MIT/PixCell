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
    # Starts at x=0 with width 0.4um and tapers down to a sharp point (0.02um) over 24um
    taper = c << gf.components.taper(
        length=24.0,
        width1=0.4,
        width2=0.02,
        layer=layer
    )

    # ---------------------------------------------------------
    # 2. Parametric Path Construction for Outer Arms
    # ---------------------------------------------------------
    # We mathematically define the path coordinates (Straight -> S-Bend -> Straight)
    # This guarantees smooth tangent continuity without relying on gf.path.bezier
    
    # Part A: Straight section running parallel to the taper (Length = 24.0)
    x_straight1 = np.linspace(0, 24.0, 50)
    y_straight1 = np.full_like(x_straight1, 0.35)

    # Part B: S-Bend section using a smooth Cosine transition (Length = 10.0)
    x_sbend = np.linspace(24.0, 34.0, 50)
    # Cosine S-bend interpolation from y=0.35 to y=0.65
    y_sbend = 0.35 + (0.65 - 0.35) * (1 - np.cos(np.pi * (x_sbend - 24.0) / 10.0)) / 2

    # Part C: Final Straight section (Length = 6.0)
    x_straight2 = np.linspace(34.0, 40.0, 20)
    y_straight2 = np.full_like(x_straight2, 0.65)

    # Concatenate segments (slicing [1:] avoids duplicate points at boundaries)
    x_top = np.concatenate([x_straight1, x_sbend[1:], x_straight2[1:]])
    y_top = np.concatenate([y_straight1, y_sbend[1:], y_straight2[1:]])

    # Convert coordinates to tuple lists and create standard gf.Paths
    pts_top = [(float(x), float(y)) for x, y in zip(x_top, y_top)]
    pts_bot = [(float(x), float(-y)) for x, y in zip(x_top, y_top)]  # Mirror for bottom

    p_top = gf.Path(pts_top)
    p_bot = gf.Path(pts_bot)

    # ---------------------------------------------------------
    # 3. Path Extrusion with Width Transition
    # ---------------------------------------------------------
    # The outer arms transition in width from 0.1um to 0.4um over the entire 40um length
    xs_narrow = gf.cross_section.cross_section(width=0.1, layer=layer)
    xs_wide = gf.cross_section.cross_section(width=0.4, layer=layer)
    
    # 'sine' width_type creates a smooth adiabatic growth profile
    trans = gf.path.transition(cross_section1=xs_narrow, cross_section2=xs_wide, width_type='sine')

    # Fallback structure ensures compatibility across minor GDSFactory version changes
    try:
        arm_top = c << gf.path.extrude_transition(p_top, trans)
        arm_bot = c << gf.path.extrude_transition(p_bot, trans)
    except AttributeError:
        # Standard GDSFactory (v6/v7/v8) method
        arm_top = c << gf.path.extrude(p_top, cross_section=trans)
        arm_bot = c << gf.path.extrude(p_bot, cross_section=trans)

    # ---------------------------------------------------------
    # Footprint Verification:
    # Outer arms end at center y = ±0.65 with width 0.4.
    # Max Y = 0.65 + (0.4 / 2) = 0.85
    # Min Y = -0.65 - (0.4 / 2) = -0.85
    # Total Height = 0.85 - (-0.85) = 1.70 µm
    # Total Length = 40.0 µm
    # ---------------------------------------------------------
    
    return c

# Create the component and explicitly write it to a GDS file
if __name__ == "__main__":
    device = adiabatic_mode_converter()
    device.write_gds("adiabatic_mode_converter.gds")