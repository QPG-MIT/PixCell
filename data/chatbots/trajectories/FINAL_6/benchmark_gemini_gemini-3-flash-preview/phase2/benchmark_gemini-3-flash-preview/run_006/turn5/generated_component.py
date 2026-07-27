import gdsfactory as gf
import numpy as np

@gf.cell
def petal_cross_v5():
    """
    Fifth iteration of the petal cross.
    Refines the petal profile with higher point density for smooth curves
    and adjusts the aspect ratio to better match the target image's 'leaf' shape.
    
    Footprint target: 4.7um x 4.7um
    """
    c = gf.Component("petal_cross_v5")
    
    # --- Dimensions & Scaling ---
    limit = 2.35       # Half-extent for 4.7um total size
    y_neck = 1.95      # Where the curved petal transitions to the rectangular tip
    w_max = 0.54       # Maximum half-width of the petal belly
    w_tip = 0.07       # Half-width of the rectangular tip (total 0.14um)
    
    # --- Profile Generation ---
    # We use more points to define the curved section of the petal arm
    # The profile follows a modified sine-like curve for a natural leaf silhouette
    num_curve_points = 15
    y_curve = np.linspace(0, y_neck, num_curve_points)
    
    # Width function: flares out from center, reaches max, then tapers to neck
    # Using a power-scaled sine creates a slightly 'fuller' belly
    x_curve = w_max * np.sin(np.pi * y_curve / y_neck)**0.8
    
    # Assemble the right-side profile points
    profile = []
    for x, y in zip(x_curve, y_curve):
        profile.append((x, y))
        
    # Add the rectangular tip points
    profile.append((w_tip, y_neck + 0.05)) # small chamfer transition
    profile.append((w_tip, limit))         # end of tip
    
    # Mirror the profile to create a full symmetric arm
    full_x = [p[0] for p in profile] + [-p[0] for p in reversed(profile)]
    full_y = [p[1] for p in profile] + [p[1] for p in reversed(profile)]
    arm_points = list(zip(full_x, full_y))
    
    # Create the arm template
    arm = gf.Component("arm_template")
    arm.add_polygon(arm_points, layer=(1, 0))
    
    # --- Assembly ---
    # Place four rotated instances of the arm
    for angle in [0, 90, 180, 270]:
        ref = c << arm
        ref.rotate(angle)
        
    # Add a tiny central core to bridge the petals smoothly at the origin
    # Reduced radius from v4 to maintain the sharp inward 'V' look
    c << gf.components.circle(radius=0.12, layer=(1, 0))

    # Merge overlapping geometries into a single clean polygon
    device = gf.boolean(A=c, B=c, operation="or", layer=(1, 0))
    
    return device

if __name__ == "__main__":
    component = petal_cross_v5()
    component.write_gds("petal_cross_v5.gds")
    
    print(f"Device: {component.name}")
    print(f"Dimensions: {component.xsize:.2f} um x {component.ysize:.2f} um")