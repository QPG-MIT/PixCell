import gdsfactory as gf
import numpy as np

@gf.cell
def device_cross_flower_v4():
    """
    Generates a 4-port cross device with 'flower' shaped arms.
    Matches target dimensions: 4.7um x 4.7um footprint.
    """
    c = gf.Component()

    # --- Dimensions & Constraints ---
    # Target Footprint: 4.7um x 4.7um => Radius = 2.35um
    radius = 2.35
    
    # Geometrical features estimated from visual target
    # The arm consists of a "petal" (bulb) and a "stem" (waveguide tip).
    length_stem = 0.55      # Length of the straight tip section
    length_bulb = radius - length_stem # 1.8um
    
    # Widths refined for more elegant/slender proportions
    width_center = 0.16     # Narrow connection at center to create distinct petals
    width_stem = 0.12       # Very thin waveguide tip
    width_max = 0.78        # Max width of the petal (reduced from previous version)
    
    layer = (1, 0)

    # --- Geometry Generation (Sine Profile) ---
    # We use a sine-based profile for the bulb to create a smooth, leaf-like shape.
    # w(x) = Linear_Trend(x) + Sine_Bump(x)
    
    n_points = 101
    x_bulb = np.linspace(0, length_bulb, n_points)
    
    # 1. Base linear taper from center width to stem width
    # This ensures exact matching of widths at x=0 and x=L_bulb
    w_linear = width_center + (width_stem - width_center) * (x_bulb / length_bulb)
    
    # 2. Additive Sine bump to create the volume
    # We calculate amplitude such that the peak roughly hits width_max.
    # The linear baseline at the middle is approx (width_center + width_stem)/2
    mid_linear = (width_center + width_stem) / 2.0
    bump_amplitude = width_max - mid_linear
    
    # Sin(pi*x/L) creates a single symmetric arch
    w_bump = bump_amplitude * np.sin(np.pi * x_bulb / length_bulb)
    
    # Total half-width profile
    y_bulb = (w_linear + w_bump) / 2.0
    
    # 3. Stem Section (Constant rectangular width)
    x_stem = np.array([length_bulb, radius])
    y_stem = np.array([width_stem/2.0, width_stem/2.0])
    
    # Combine coordinates
    x_upper = np.concatenate([x_bulb, x_stem])
    y_upper = np.concatenate([y_bulb, y_stem])
    
    # Create polygon points (Top half and mirrored Bottom half)
    pts_upper = np.column_stack([x_upper, y_upper])
    pts_lower = np.column_stack([x_upper, -y_upper])[::-1]
    pts = np.concatenate([pts_upper, pts_lower])

    # --- Component Assembly ---
    # Create a single arm component
    arm = gf.Component()
    arm.add_polygon(pts, layer=layer)
    
    # Add port at the tip
    arm.add_port(
        name="o1",
        center=(radius, 0),
        width=width_stem,
        orientation=0,
        layer=layer
    )

    # Rotate and place 4 instances to form the cross
    for i, angle in enumerate([0, 90, 180, 270]):
        ref = c << arm
        ref.rotate(angle)
        # Expose ports o1, o2, o3, o4
        c.add_port(f"o{i+1}", port=ref.ports["o1"])

    return c

if __name__ == "__main__":
    device = device_cross_flower_v4()
    device.write_gds("device_cross_flower_v4.gds")
    
    # Print info
    print(f"Device Size: {device.size_info.width:.2f} um x {device.size_info.height:.2f} um")