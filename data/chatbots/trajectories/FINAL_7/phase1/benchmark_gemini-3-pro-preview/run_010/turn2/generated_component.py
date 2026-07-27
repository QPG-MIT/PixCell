import gdsfactory as gf
import numpy as np

@gf.cell
def pinched_racetrack_mzi_v3():
    """
    Recreates the pinched racetrack 'dogbone' device with sharp diagonal transitions.
    Uses custom CrossSection to allow tight bends and Paths for polygonal geometry.
    """
    c = gf.Component()

    # --- 1. Parameters & Custom Cross-Section ---
    wg_width = 0.5
    layer_wg = (1, 0)
    layer_heater = (2, 0)

    # Define a custom cross-section with radius_min=0.1 to allow tight geometry
    # and prevent the "ValueError: min_bend_radius..."
    xs = gf.cross_section.cross_section(
        width=wg_width,
        layer=layer_wg,
        radius_min=0.1 
    )

    # --- 2. Geometry Constraints ---
    total_h = 3.0
    
    # Vertical Dimensions
    # Height = 3.0 -> Radius = 1.5 (Outer edge).
    # Centerline Radius = 1.5 - (0.5/2) = 1.25
    r_center = 1.25
    
    # Inner straight pinch
    # Gap between inner arms approx 0.5um
    gap = 0.5
    y_inner = (gap + wg_width) / 2  # 0.5
    
    # Horizontal Dimensions
    # Anchor points for the "Dogbone" shape
    x_arc = 1.25         # X-coordinate where the straight section meets the 180 loop
    x_straight = 0.75    # X-coordinate where the diagonal pinch starts

    # --- 3. Build Traces (Top and Bottom) using Paths ---
    # We use Paths to create the "Straight -> Diagonal -> Straight" shapes 
    # This guarantees the sharp corners (kinks) seen in the reference image.

    # Top Trace Points: (Left Arc Top) -> (Left Pinch) -> (Right Pinch) -> (Right Arc Top)
    pts_top = [
        (-x_arc, r_center),
        (-x_straight, y_inner),
        (x_straight, y_inner),
        (x_arc, r_center)
    ]
    
    # Create and extrude top path
    p_top = gf.Path(pts_top)
    trace_top = c << p_top.extrude(xs)
    
    # Bottom Trace Points: (Left Arc Bot) -> (Left Pinch) -> (Right Pinch) -> (Right Arc Bot)
    pts_bot = [
        (-x_arc, -r_center),
        (-x_straight, -y_inner),
        (x_straight, -y_inner),
        (x_arc, -r_center)
    ]
    
    # Create and extrude bottom path
    p_bot = gf.Path(pts_bot)
    trace_bot = c << p_bot.extrude(xs)

    # --- 4. End Loops (180 degree circular bends) ---
    
    # Right Loop
    # We use a standard 180 circular bend.
    # Its ports are naturally at (0,0) and (0, 2*R).
    # We move it so its 'o2' port connects to the end of the top path.
    loop_r = c << gf.components.bend_circular(radius=r_center, angle=180, cross_section=xs)
    
    # Position logic:
    # Target position for o2 is (x_arc, r_center) -> (1.25, 1.25)
    # Default position of o2 is (0, 2*r_center) -> (0, 2.5)
    # Move vector = Target - Default = (1.25, -1.25)
    loop_r.move((1.25, -1.25))

    # Left Loop
    # Create, Mirror X, then Move
    loop_l = c << gf.components.bend_circular(radius=r_center, angle=180, cross_section=xs)
    loop_l.mirror(p1=(0,0), p2=(0,1)) # Mirror across Y-axis
    
    # Position logic for Left Loop (after mirror):
    # Target for o2 is (-x_arc, r_center) -> (-1.25, 1.25)
    # Current o2 (after mirror) is (0, 2.5)
    # Move vector = (-1.25, -1.25)
    loop_l.move((-1.25, -1.25))

    # --- 5. Heater Pads ---
    pad_w = 0.5
    pad_h = 0.4
    x_pad_dist = 0.35
    
    # Place pads on the inner straight sections
    for y in [y_inner, -y_inner]:
        # Left
        h1 = c << gf.components.rectangle(size=(pad_w, pad_h), layer=layer_heater, centered=True)
        h1.move((-x_pad_dist, y))
        # Right
        h2 = c << gf.components.rectangle(size=(pad_w, pad_h), layer=layer_heater, centered=True)
        h2.move((x_pad_dist, y))

    return c

if __name__ == "__main__":
    device = pinched_racetrack_mzi_v3()
    
    # Show in KLayout (if installed/configured)
    device.show()
    
    # Save to GDS
    gds_path = "pinched_racetrack_final.gds"
    device.write_gds(gds_path)
    print(f"GDS file saved to: {gds_path}")
    
    # Robust Size Check (Handles different GDSFactory backends)
    try:
        if hasattr(device, "dbbox"):
            # KFactory backend
            bb = device.dbbox()
            print(f"Device Size: {bb.width():.2f} x {bb.height():.2f} um")
        else:
            # Standard GDSFactory backend
            bbox = device.bbox
            w = bbox[1][0] - bbox[0][0]
            h = bbox[1][1] - bbox[0][1]
            print(f"Device Size: {w:.2f} x {h:.2f} um")
    except Exception as e:
        print(f"Could not print size due to backend difference: {e}")