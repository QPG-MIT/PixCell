import gdsfactory as gf
import numpy as np

@gf.cell
def device_design():
    """
    Generates a 4-petal device based on visual target.
    
    Key Design Features:
    - 4-fold rotational symmetry.
    - "Fat" petal shape modeled by a sine wave to create a convex lens profile.
    - Narrow star-shaped gap at the center (achieved by tuning the start slope of the petal).
    - Distinct rectangular tips protruding from the petal ends.
    - Dimensions constrained to fit a 4.7um x 4.7um footprint.
    """
    c = gf.Component()

    # 1. Define Dimensions
    # The device fits in a 4.7um box, so the max radius is 2.35um.
    R_total = 2.35
    
    # Parameters estimated from the target image to match proportions:
    # The tip is a straight stick, roughly 30% of the radius.
    L_tip = 0.70          
    W_tip = 0.18          
    
    # The petal body covers the rest of the radius.
    L_petal = R_total - L_tip
    
    # Max width of the petal. 
    # Increasing this makes the petals "fatter", reducing the gap at the center 
    # to match the narrow star-shaped negative space in the target.
    W_petal_max = 1.0     

    # 2. Generate Custom Petal Geometry
    # We use a sine wave profile: y(x) = A * sin(k * x)
    # This shape tapers from 0 width at the center, bulges to W_petal_max, 
    # and tapers down to W_tip at the connection point.
    
    A = W_petal_max / 2.0
    
    # Calculate wave number 'k' such that width is W_tip at x = L_petal.
    # We select the solution on the falling edge of the sine wave (angle > pi/2)
    # so the petal reaches its max width and then narrows before the tip.
    target_half_width = W_tip / 2.0
    ratio = np.clip(target_half_width / A, 0, 1) # Safety clip
    
    # arcsin gives the first crossing (rising edge); pi - arcsin gives the falling edge.
    angle_end = np.pi - np.arcsin(ratio)
    k = angle_end / L_petal
    
    # Generate profile points
    N_points = 300
    x = np.linspace(0, L_petal, N_points)
    y = A * np.sin(k * x)
    
    # Build polygon coordinates
    pts_top = np.column_stack((x, y))
    pts_bot = np.column_stack((x, -y))
    # Combine top and reversed bottom to form a closed loop
    pts = np.vstack((pts_top, pts_bot[::-1]))
    
    # Create the petal component
    petal = gf.Component("petal_primitive")
    petal.add_polygon(pts, layer=(1, 0))

    # 3. Create the Tip Geometry
    # A simple rectangle attached to the end of the petal.
    tip = gf.components.rectangle(size=(L_tip, W_tip), layer=(1, 0), centered=True)

    # 4. Assemble one Arm (Petal + Tip)
    arm = gf.Component("arm")
    
    # Add petal (starts at 0,0)
    arm << petal
    
    # Add tip
    # The rectangle is centered at (0,0) with width L_tip. It spans [-L_tip/2, L_tip/2].
    # We want it to start at L_petal and end at L_petal + L_tip.
    # Therefore, we move its center to L_petal + L_tip/2.
    t_ref = arm << tip
    t_ref.move((L_petal + L_tip/2.0, 0))

    # 5. Arrange 4 Arms into the Device
    for angle in [0, 90, 180, 270]:
        ref = c << arm
        ref.rotate(angle)

    return c

if __name__ == "__main__":
    component = device_design()
    component.write_gds("device_design.gds")
    component.show()