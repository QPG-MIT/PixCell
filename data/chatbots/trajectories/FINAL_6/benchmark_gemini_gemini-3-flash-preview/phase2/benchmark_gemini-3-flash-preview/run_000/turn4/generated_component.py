import gdsfactory as gf
import numpy as np

@gf.cell
def recreate_exact_device():
    """
    Recreates the 4-petal device using a custom polygon profile.
    This matches the sharp 'V' valleys and leaf-like petal curvature.
    
    Footprint: 4.7um x 4.7um (Fixed)
    """
    c = gf.Component("target_device_v4")
    layer = (1, 0)
    
    # --- Dimensions for 4.7um Total Footprint ---
    half_footprint = 2.35  # Half of 4.7um
    pin_width = 0.32
    pin_length = 0.45
    petal_length = half_footprint - pin_length  # ~1.9um
    
    # --- Define the Arm Profile (one horizontal arm) ---
    # We define a set of points that taper from the center to a wide belly,
    # then narrow down to meet the rectangular pin.
    
    # x-coordinates along the arm
    x_pts = [0.0, 0.2, 0.5, 1.0, 1.5, 1.9, 2.35]
    
    # half-widths at those points (y-coordinates)
    # y=0.02 at x=0 creates the sharp 'star' center valley
    y_h_width = [0.02, 0.15, 0.35, 0.58, 0.45, 0.16, 0.16]
    
    # Combine into a single symmetric polygon for one arm
    upper_half = list(zip(x_pts, y_h_width))
    lower_half = list(zip(reversed(x_pts), [-y for y in reversed(y_h_width)]))
    arm_polygon_points = upper_half + lower_half
    
    # Create the base arm component
    arm = gf.Component("arm_unit")
    arm.add_polygon(arm_polygon_points, layer=layer)
    
    # --- Place 4 arms with 90-degree rotations ---
    for angle in [0, 90, 180, 270]:
        ref = c << arm
        ref.rotate(angle)
    
    # --- Final Polish ---
    # Boolean OR the parts to create one clean manifold shape
    # This removes any internal lines at the origin.
    merged = gf.boolean(A=c, B=c, operation="or", layer=layer)
    
    final_output = gf.Component("final_recreation")
    final_output << merged
    
    return final_output

if __name__ == "__main__":
    # Generate component
    component = recreate_exact_device()
    
    # Fix for the subscriptable error: 
    # Use xsize and ysize properties which are safer across versions
    w = component.xsize
    h = component.ysize
    
    print(f"Verified Footprint: {w:.2f}um x {h:.2f}um")
    
    # Export GDS
    filename = "refined_device_v4.gds"
    component.write_gds(filename)
    
    # If running locally, you can view it:
    # component.show()