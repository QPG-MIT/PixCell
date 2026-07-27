# SCALED version - target: 40.0 x 1.7 µm
# Original dimensions: 40.00 x 1.68 µm
# Scale factors: SCALE_X = 1.000000, SCALE_Y = 1.011905

import gdsfactory as gf
import numpy as np

@gf.cell
def tapered_s_bend(
    length: float = 10.0,
    height: float = 2.0,
    width_in: float = 0.5,
    width_out: float = 0.5,
    layer: tuple = (1, 0)
):
    """
    Generates a cosine S-bend with linearly varying width.
    """
    c = gf.Component()
    
    # Increased resolution for smoother rendering of long bends
    n_points = 201
    t = np.linspace(0, 1, n_points)
    
    # Cosine S-bend trajectory
    # x goes from 0 to length
    # y goes from 0 to height using (1 - cos)/2 shape
    x = length * t
    y = height * (1 - np.cos(np.pi * t)) / 2
    
    # Linear width tapering
    w = width_in + (width_out - width_in) * t
    
    # Calculate angles for normals to correctly offset the polygon edges
    # dy/dx = (dy/dt) / (dx/dt)
    # dy/dt = height * pi/2 * sin(pi*t)
    # dx/dt = length
    dydx = (height * np.pi * np.sin(np.pi * t) / 2) / length
    angles = np.arctan(dydx)
    
    # Create polygon points for the "thick" path
    # Top edge
    x_top = x - (w / 2) * np.sin(angles)
    y_top = y + (w / 2) * np.cos(angles)
    
    # Bottom edge
    x_bot = x + (w / 2) * np.sin(angles)
    y_bot = y - (w / 2) * np.cos(angles)
    
    # Concatenate to form a closed polygon
    points = np.concatenate([
        np.stack([x_top, y_top], axis=1),
        np.stack([x_bot, y_bot], axis=1)[::-1]
    ])
    
    c.add_polygon(points, layer=layer)
    
    # Add ports for connectivity
    c.add_port(name="o1", center=(0, 0), width=width_in, orientation=180, layer=layer)
    c.add_port(name="o2", center=(length, height), width=width_out, orientation=0, layer=layer)
    
    return c

@gf.cell
def trident_mode_converter(
    # Center arm parameters
    mid_length: float = 16.0,      # Increased from 12.15 to fix blue gap at tip
    mid_width_in: float = 0.22,    # Reduced from 0.306 to reduce red width error
    mid_width_out: float = 0.10,   # Sharpened tip
    
    # Outer arm straight parameters
    outer_length: float = 24.8,    # Maintained length
    outer_width_in: float = 0.10,  # Maintained thin input
    outer_width_out: float = 0.14, # Reduced from 0.238 to remove red bulge at bend start
    gap_start: float = 0.05,       # Slight increase for better separation with thinner guides
    
    # Outer arm bend parameters
    bend_length: float = 15.2,     # Maintained length
    bend_height: float = 0.50,     # Increased from 0.374 to compensate for thinner arms (maintains total device height)
    bend_width_end: float = 0.26,  # Drastically reduced from 0.476 to fix massive red overshoot
    layer: tuple = (1, 0)
):
    """
    Improved Trident Mode Converter.
    Optimized based on difference analysis:
    1. Thinned all waveguides significantly to match the delicate target structure.
    2. Extended central arm to match target length.
    3. Adjusted bend height to maintain total aperture despite thinner arms.
    """
    c = gf.Component()

    # --- 1. Center Arm ---
    # Tapered central waveguide
    center = c << gf.components.taper(
        length=mid_length,
        width1=mid_width_in,
        width2=mid_width_out,
        layer=layer
    )
    # Center is at (0,0)

    # --- 2. Layout Calculations ---
    # Calculate vertical offset for outer arms based on starting gap
    y_offset = (mid_width_in / 2) + gap_start + (outer_width_in / 2)

    # --- 3. Top Arm ---
    # Straight section
    top_s = c << gf.components.taper(
        length=outer_length,
        width1=outer_width_in,
        width2=outer_width_out,
        layer=layer
    )
    top_s.movey(y_offset)

    # Widening S-Bend
    top_b = c << tapered_s_bend(
        length=bend_length,
        height=bend_height,
        width_in=outer_width_out,
        width_out=bend_width_end,
        layer=layer
    )
    # Connect bend to straight section
    top_b.connect("o1", top_s.ports["o2"])

    # --- 4. Bottom Arm ---
    # Straight section
    bot_s = c << gf.components.taper(
        length=outer_length,
        width1=outer_width_in,
        width2=outer_width_out,
        layer=layer
    )
    bot_s.movey(-y_offset)

    # Widening S-Bend (negative height)
    bot_b = c << tapered_s_bend(
        length=bend_length,
        height=-bend_height,
        width_in=outer_width_out,
        width_out=bend_width_end,
        layer=layer
    )
    bot_b.connect("o1", bot_s.ports["o2"])

    return c

if __name__ == "__main__":
    # Create the improved device
    device = trident_mode_converter(
    mid_length=16.000000,  # 16.0 * 1.0000 rounded
    mid_width_in=0.222000,  # 0.22 * 1.0119 rounded
    mid_width_out=0.102000,  # 0.1 * 1.0119 rounded
    outer_length=24.800000,  # 24.8 * 1.0000 rounded
    outer_width_in=0.102000,  # 0.1 * 1.0119 rounded
    outer_width_out=0.142000,  # 0.14 * 1.0119 rounded
    gap_start=0.050000,  # 0.05 * 1.0119 rounded
    bend_length=15.200000,  # 15.2 * 1.0000 rounded
    bend_height=0.506000,  # 0.5 * 1.0119 rounded
    bend_width_end=0.264000,  # 0.26 * 1.0119 rounded
)
    
    # Write GDS
    gds_path = device.write_gds("trident_mode_converter_improved_SCALED.gds")
    print(f"GDS file saved to: {gds_path}")