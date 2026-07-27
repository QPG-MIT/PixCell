import gdsfactory as gf

@gf.cell
def recreate_cross_device_v3():
    """
    Recreates the cross-shaped device.
    Fixed connectivity and size attribute usage.
    Footprint constraint: 4.7um x 4.7um
    """
    c = gf.Component("refined_cross_device")
    
    # 1. Dimensions for 4.7um footprint (Radius = 2.35um)
    petal_length = 1.85  
    tip_length = 0.50    # 1.85 + 0.50 = 2.35um (Center to edge)
    petal_width = 1.0    
    tip_width = 0.25     
    
    # 2. Create Primitives
    # Ellipse is centered at (0,0). radii is (half-length, half-width)
    petal = gf.components.ellipse(radii=(petal_length / 2, petal_width / 2), layer=(1, 0))
    
    # Rectangle origin is at (0,0)
    tip = gf.components.rectangle(size=(tip_length, tip_width), layer=(1, 0))
    
    # 3. Assemble one arm
    arm = gf.Component("arm_unit")
    
    # Move petal so its left edge is at x=0
    p_ref = arm << petal
    p_ref.movex(petal_length / 2)
    
    # Move tip so its left edge is at the end of the petal (x=petal_length)
    # and center it vertically (y=0)
    t_ref = arm << tip
    t_ref.movex(petal_length)
    t_ref.movey(-tip_width / 2)
    
    # 4. Assemble the full cross using rotational symmetry
    for angle in [0, 90, 180, 270]:
        arm_ref = c << arm
        arm_ref.rotate(angle)
    
    # 5. Perform Boolean OR to merge the parts into one seamless polygon
    merged = gf.boolean(A=c, B=c, operation="or", layer=(1, 0))
    
    return merged

if __name__ == "__main__":
    # Create the component
    device = recreate_cross_device_v3()
    
    # Write GDS
    device.write_gds("cross_device_final.gds")
    
    # Correct way to access size in modern GDSFactory/KFactory:
    # .dxsize and .dysize give the width and height in microns.
    print(f"Device width: {device.dxsize:.2f} um")
    print(f"Device height: {device.dysize:.2f} um")
    
    # Show the component
    device.show()