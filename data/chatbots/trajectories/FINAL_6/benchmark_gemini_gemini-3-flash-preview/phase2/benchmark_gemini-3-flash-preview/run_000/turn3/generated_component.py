import gdsfactory as gf

@gf.cell
def recreate_exact_device():
    """
    Recreates the 4-petal device using elliptical primitives to match the 
    convex leaf-like curvature and sharp interior valleys.
    
    Footprint: 4.7um x 4.7um
    """
    c = gf.Component("recreated_device_v3")
    layer = (1, 0)
    
    # --- Dimensions for 4.7um Footprint ---
    total_footprint = 4.7
    half_footprint = total_footprint / 2  # 2.35um
    
    # Pin (stub) dimensions
    pin_length = 0.4
    pin_width = 0.32
    
    # Petal (ellipse) dimensions
    # The petal length must be the remainder of the half-footprint
    petal_length = half_footprint - pin_length # 1.95um
    
    # Ellipse radii: 
    # rx is half the petal length because the ellipse spans 2*rx
    rx = petal_length / 2  # 0.975um
    # ry controls the 'plumpness' of the petal. 
    # Visual estimate from target image suggests a max width of ~1.1um
    ry = 0.55  
    
    # 1. Create one 'Arm' component
    arm = gf.Component()
    
    # Create the petal using an ellipse
    petal = arm << gf.components.ellipse(radii=(rx, ry), layer=layer)
    # Position ellipse so its left tip is at (0,0)
    petal.movex(rx) 
    
    # Create the pin
    pin = arm << gf.components.rectangle(size=(pin_length, pin_width), layer=layer, centered=True)
    # Position pin at the tip of the petal
    pin.movex(petal_length + pin_length/2)
    
    # 2. Place 4 arms with 90-degree rotations around the origin
    for angle in [0, 90, 180, 270]:
        arm_ref = c << arm
        arm_ref.rotate(angle)
    
    # 3. Final cleanup: Merge all overlapping primitives into one clean polygon
    # This creates the single manifold black shape shown in the target image.
    merged = gf.boolean(A=c, B=c, operation="or", layer=layer)
    
    output = gf.Component("final_device")
    output << merged
    
    # Optional: Add ports if this were for a functional circuit, 
    # but for pure visual recreation, the geometry is now complete.
    
    return output

if __name__ == "__main__":
    # Generate the component
    component = recreate_exact_device()
    
    # Export GDS
    filename = "device_recreation_v3.gds"
    component.write_gds(filename)
    
    print(f"Successfully generated: {filename}")
    # The resulting footprint is confirmed at 4.7um x 4.7um