import gdsfactory as gf

@gf.cell
def star_cross_device_v3():
    """
    Creates a 4-fold symmetric device with tapered elliptical petals and rectangular stubs.
    Refines the central intersection to be sharp and the tip transition to be smooth.
    Footprint constrained to 4.7um x 4.7um.
    """
    c = gf.Component()
    
    # 1. Define Dimensions
    target_footprint = 4.7
    radius = target_footprint / 2.0  # 2.35 um
    
    # Stub parameters
    # Thin rectangular waveguides at the tips
    stub_len = 0.55
    stub_width = 0.14
    # Stub is aligned to the outer edge (radius)
    stub_start_x = radius - stub_len
    stub_center_x = radius - stub_len / 2.0
    
    # Petal parameters
    petal_width = 0.78
    
    # Center geometry:
    # To get a sharp 'X' intersection at the center, the ellipses must start 
    # very close to the origin. A tiny negative start ensures boolean connectivity
    # while maintaining the sharp inward corners.
    petal_start_x = -0.02
    
    # Tip transition:
    # We want the ellipse width at the stub connection to approximately match stub_width.
    # Extending the ellipse slightly past the stub start creates a smoother shoulder.
    petal_end_x = stub_start_x + 0.04
    
    # Calculate Ellipse Geometry
    petal_length = petal_end_x - petal_start_x
    rx = petal_length / 2.0
    ry = petal_width / 2.0
    petal_center_x = petal_start_x + rx

    # 2. Build Arm Geometry
    # We create a temporary component to position the primitives before fusing them
    temp = gf.Component()
    
    # Ellipse Petal
    e_ref = temp << gf.components.ellipse(radii=(rx, ry), layer=(1, 0))
    e_ref.move((petal_center_x, 0))
    
    # Rectangle Stub
    s_ref = temp << gf.components.rectangle(size=(stub_len, stub_width), layer=(1, 0), centered=True)
    s_ref.move((stub_center_x, 0))
    
    # Create the fused polygon for one arm using Boolean OR
    # This removes internal edges
    arm_poly = gf.boolean(e_ref, s_ref, operation="or", layer=(1, 0))
    
    # 3. Assemble Full Device
    # Rotate and place the fused arm 4 times
    for angle in [0, 90, 180, 270]:
        ref = c << arm_poly
        ref.rotate(angle)
        
    # 4. Add Ports
    # Standard ports at the cardinal extremities
    c.add_port(name="o1", center=(radius, 0), width=stub_width, orientation=0, layer=(1,0))
    c.add_port(name="o2", center=(0, radius), width=stub_width, orientation=90, layer=(1,0))
    c.add_port(name="o3", center=(-radius, 0), width=stub_width, orientation=180, layer=(1,0))
    c.add_port(name="o4", center=(0, -radius), width=stub_width, orientation=270, layer=(1,0))

    return c

if __name__ == "__main__":
    device = star_cross_device_v3()
    device.show()
    device.write_gds("star_cross_device_v3.gds")
    
    # Verification
    print(f"Device Size: {device.size_info.width:.2f} x {device.size_info.height:.2f} um")