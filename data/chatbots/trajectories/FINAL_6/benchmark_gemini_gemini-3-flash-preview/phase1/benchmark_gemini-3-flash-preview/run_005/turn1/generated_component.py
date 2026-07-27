import gdsfactory as gf

@gf.cell
def recreate_cross_device():
    """
    Recreates the 4-lobed cross device geometry.
    Footprint constraint: 4.7um x 4.7um.
    """
    c = gf.Component("cross_device")
    
    # Total half-span is 2.35 um (4.7 / 2)
    half_len = 2.35
    
    # We define the arm by an elliptical 'petal' and a rectangular 'tip'
    tip_length = 0.4
    petal_length = half_len - tip_length  # 1.95 um
    
    # Width parameters based on visual inspection
    petal_width = 1.0  # Total width of the petal at its widest point
    tip_width = 0.22   # Standard narrow tip width
    
    # 1. Create a single 'arm' pointing East (+X)
    arm = gf.Component("arm_template")
    
    # Petal: gf.components.ellipse uses 'radii' (half-lengths)
    # To get a petal of length 1.95, x_radius = 1.95 / 2
    petal = arm << gf.components.ellipse(
        radii=(petal_length / 2, petal_width / 2), 
        layer=(1, 0)
    )
    # Move the ellipse so its edge starts at the center (0,0)
    petal.movex(petal_length / 2)
    
    # Tip: Rectangular segment at the end of the petal
    tip = arm << gf.components.rectangle(
        size=(tip_length, tip_width), 
        layer=(1, 0), 
        centered=True
    )
    # Position tip to start exactly where the petal ends (at x = 1.95)
    tip.movex(petal_length + tip_length / 2)
    
    # 2. Place 4 rotated copies of the arm to create the cross
    for angle in [0, 90, 180, 270]:
        arm_ref = c << arm
        arm_ref.rotate(angle)
    
    # 3. Use boolean OR to merge the overlapping primitives into a single shape
    # This matches the solid silhouette from the image.
    merged_device = gf.boolean(A=c, B=c, operation="or", layer=(1, 0))
    
    return merged_device

if __name__ == "__main__":
    # Generate the component
    device = recreate_cross_device()
    
    # FIX: Use dxsize and dysize instead of .size to avoid AttributeError
    w = device.dxsize
    h = device.dysize
    
    print(f"Calculated Device Dimensions: {w:.2f} um x {h:.2f} um")
    
    # Export and visualize
    device.write_gds("recreated_device.gds")
    device.show()