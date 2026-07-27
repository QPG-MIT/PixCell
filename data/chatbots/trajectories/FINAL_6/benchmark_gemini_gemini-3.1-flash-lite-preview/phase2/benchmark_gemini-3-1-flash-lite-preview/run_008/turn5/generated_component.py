import gdsfactory as gf

@gf.cell
def custom_clover():
    """
    Creates a seamless, four-petaled clover/star geometry.
    Petals meet at the center (0,0) and include a rectangular stem protrusion.
    """
    layer = (1, 0)
    
    # 1. Define the petal points (counter-clockwise)
    # The petal base is from (-0.2, 0) to (0.2, 0).
    # This ensures that when rotated, the bases meet at the origin,
    # forming a 0.4x0.4 square at the center that merges seamlessly.
    petal_pts = [
        (-0.2, 0),      # base left
        (0.2, 0),       # base right
        (0.6, 0.8),     # widest bulge right
        (0.2, 1.8),     # stem base right
        (0.2, 2.3),     # stem top right
        (-0.2, 2.3),    # stem top left
        (-0.2, 1.8),    # stem base left
        (-0.6, 0.8)     # widest bulge left
    ]
    
    # 2. Create the petal component
    petal = gf.Component()
    petal.add_polygon(petal_pts, layer=layer)
    
    # 3. Create two components, each with 2 petals.
    # We split into two components to facilitate a clean boolean OR merge.
    c1 = gf.Component()
    (c1 << petal).rotate(0, center=(0, 0))
    (c1 << petal).rotate(90, center=(0, 0))
    
    c2 = gf.Component()
    (c2 << petal).rotate(180, center=(0, 0))
    (c2 << petal).rotate(270, center=(0, 0))
    
    # 4. Perform Boolean OR to merge everything into one seamless polygon
    final_clover = gf.boolean(c1, c2, operation="or", layer=layer)
    
    return final_clover

if __name__ == "__main__":
    # Create the component
    device = custom_clover()
    
    # Save the file
    device.write_gds("clover_shape.gds")
    
    print("GDS file 'clover_shape.gds' produced successfully.")
    
    # Display the result
    device.show()