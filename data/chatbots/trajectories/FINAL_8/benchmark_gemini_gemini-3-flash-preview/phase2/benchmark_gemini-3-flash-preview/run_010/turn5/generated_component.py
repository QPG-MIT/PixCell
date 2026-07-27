import gdsfactory as gf
import numpy as np

@gf.cell
def recreate_target_device():
    """
    Turn 5 Refinement:
    - Steepens flares using a smaller radius and higher angle.
    - Ensures a clear gap between the center 5-line bundle and the outer blocks.
    - Refines cross-sections for a 1-thick + 4-thin line profile.
    - Strictly fits 120um x 4um footprint.
    """
    c = gf.Component("target_device_v5")
    layer = (1, 0)
    
    # 1. PARAMETERS
    total_width = 120.0
    # Higher angle and small radius for that steep, "U-shape" flare look
    flare_radius = 5.0 
    flare_angle = 45.0  # Steep enough to be visible, shallow enough to fit 4um
    
    # 2. PATH CONSTRUCTION
    # Create the right-hand flare segment
    p_right_curve = gf.path.euler(radius=flare_radius, angle=flare_angle)
    
    # Calculate horizontal span of the flare to center the straight section
    dx_flare = p_right_curve.points[-1][0] - p_right_curve.points[0][0]
    straight_len = total_width - (2 * dx_flare)
    p_mid = gf.path.straight(length=straight_len)
    
    # Create the left-hand flare by mirroring and reversing the curve
    p_left_pts = p_right_curve.points.copy()
    p_left_pts[:, 0] *= -1 
    p_left_curve = gf.Path(p_left_pts[::-1]) 
    
    # Assemble the full flaring path (centered horizontally)
    full_path = p_left_curve + p_mid + p_right_curve
    full_path.move((-total_width/2, 0))

    # 3. CROSS-SECTIONS
    # bundle of 5 thin lines for the center
    xs_center = gf.cross_section.cross_section(
        sections=[
            gf.Section(width=0.05, offset=y, layer=layer) 
            for y in np.linspace(-0.5, 0.5, 5) # Spaced 0.25um apart
        ]
    )
    
    # Flaring block: 1 thick base (0.6um) + 4 thin lines (0.05um)
    # We use offsets to stack them on one side of the path
    xs_flaring = gf.cross_section.cross_section(
        sections=[
            gf.Section(width=0.6, offset=-0.3, layer=layer),   # Base (bottom edge at path -0.6)
            gf.Section(width=0.05, offset=0.15, layer=layer),  # Line 1
            gf.Section(width=0.05, offset=0.30, layer=layer),  # Line 2
            gf.Section(width=0.05, offset=0.45, layer=layer),  # Line 3
            gf.Section(width=0.05, offset=0.60, layer=layer),  # Line 4
        ]
    )

    # 4. ASSEMBLY
    # Center Bundle (Static straight lines)
    c << gf.components.straight(length=total_width, cross_section=xs_center)

    # Top Block (Flares UP)
    # Positioned at y=1.0. Base bottom is at 0.4 (clear gap from center 0.5)
    # Topmost line is at ~1.63 in the center, and curves up at ends to ~2.0
    top_geo = gf.path.extrude(full_path, cross_section=xs_flaring)
    top_ref = c << top_geo
    top_ref.y = 1.0

    # Bottom Block (Flares DOWN)
    # Mirroring the top block across the X-axis
    bottom_ref = c << top_geo
    bottom_ref.mirror((1, 0)) 
    bottom_ref.y = -1.0

    return c

if __name__ == "__main__":
    device = recreate_target_device()
    
    # Export for verification
    filename = "target_device_v5.gds"
    device.write_gds(filename)
    
    print(f"Success: Turn 5 geometry rendered to {filename}")