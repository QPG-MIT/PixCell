import gdsfactory as gf
import numpy as np

@gf.cell
def star_cross_device():
    """
    Creates a star/flower shaped cross device matching the provided target image.
    
    Refinements V4:
    - Addressed the "blob" issue from V3 by significantly reducing petal width (1.7 -> 1.15).
    - Refined the geometric model to constrain the ellipse:
        1. Tip connects smoothly to stub width.
        2. Base sits slightly past the center (-0.05) to ensure fusion without massive overlap.
    - This creates the deep valleys ("pinch") at the center seen in the target while maintaining connectivity.
    - Adjusted stub length to match target proportions better.
    """
    c = gf.Component()

    # 1. Define Constraints & Dimensions
    footprint = 4.7
    
    # Tuned dimensions based on visual analysis of target vs V3
    stub_length = 0.55     # Length of the straight port section (increased for distinctness)
    stub_width = 0.28      # Width of the port
    petal_width = 1.15     # Max width of the petal (reduced to create the star valleys)
    
    # 2. Geometric Calculations
    R_max = footprint / 2
    y_junction = R_max - stub_length
    
    # Ellipse Parameters
    # We define the petal as an ellipse centered at (0, yc) with radii (rx, ry).
    # rx is determined by the desired petal width.
    rx = petal_width / 2
    
    # ry is calculated to satisfy two boundary conditions:
    # A. The ellipse must be wide enough at the junction to match the stub.
    #    At y = y_junction, x = stub_width / 2.
    # B. The ellipse must extend to the center (y=0) to form the cross, 
    #    with a small overlap to ensure connectivity.
    #    We set the bottom of the ellipse at y = y_bottom.
    y_bottom = -0.05 # Negative value ensures the petals overlap slightly at the center
    
    # Analytical solution for ry based on constraints A and B:
    # Ellipse eq: (x_conn/rx)^2 + ((y_junc - yc)/ry)^2 = 1
    # substitute yc = ry + y_bottom
    # The term inside the y-squared becomes: (y_junction - y_bottom - ry) / ry
    
    x_conn = stub_width / 2
    X_ratio = x_conn / rx
    
    # Ensure physical solution exists
    if X_ratio >= 1.0:
        # Fallback if width > petal width (should not happen with chosen params)
        ry = y_junction - y_bottom
    else:
        # Solve for ry
        # X^2 + Y^2 = 1  => Y = sqrt(1 - X^2)
        # (Numerator / ry) - 1 = sqrt(1 - X^2)
        numerator = y_junction - y_bottom
        denominator = 1 + np.sqrt(1 - X_ratio**2)
        ry = numerator / denominator
        
    yc = ry + y_bottom

    # 3. Construct Single Petal
    petal = gf.Component("petal_sub")
    
    # Ellipse Body
    e = gf.components.ellipse(radii=(rx, ry), layer=(1, 0))
    # Move ellipse so its center is at (0, yc) relative to the petal origin
    ref_e = petal << e
    ref_e.movey(yc)
    
    # Rectangular Stub
    stub = gf.components.rectangle(size=(stub_width, stub_length), layer=(1, 0), centered=True)
    ref_s = petal << stub
    ref_s.movey(y_junction + stub_length / 2)
    
    # 4. Assembly (Rotational Symmetry)
    for i in range(4):
        ref = c << petal
        ref.rotate(90 * i)
    
    # 5. Define Ports
    c.add_port("o1", center=(-footprint/2, 0), width=stub_width, orientation=180, layer=(1,0))
    c.add_port("o2", center=(footprint/2, 0), width=stub_width, orientation=0, layer=(1,0))
    c.add_port("o3", center=(0, footprint/2), width=stub_width, orientation=90, layer=(1,0))
    c.add_port("o4", center=(0, -footprint/2), width=stub_width, orientation=270, layer=(1,0))
    
    return c

# Create and save
device = star_cross_device()
device.write_gds("star_cross_refined_v4.gds")