import gdsfactory as gf

@gf.cell
def custom_clover():
    """
    Creates a clover/star geometry by merging 4 leaf-shaped petals
    and 4 rectangular tips into a single, seamless polygon.
    """
    c = gf.Component()
    layer = (1, 0)
    
    # 1. Define the base shapes
    # Ellipse (petal body) and Rectangle (tip)
    petal_body = gf.components.ellipse(radii=(0.6, 2.0), layer=layer)
    tip = gf.components.rectangle(size=(0.4, 0.4), layer=layer, centered=True)
    
    # 2. Create a single 'leaf' unit (Body + Tip)
    leaf = gf.Component()
    # Add body
    leaf << petal_body
    # Add tip at the top of the body (y=2.0)
    t_ref = leaf << tip
    t_ref.movey(2.0)
    
    # 3. Create the 4-leaf clover component
    # We add 4 references of the 'leaf' component
    clover_raw = gf.Component()
    for angle in [0, 90, 180, 270]:
        ref = clover_raw << leaf
        ref.rotate(angle)
        
    # 4. Merge all geometry into a single seamless polygon
    # gf.boolean with operation 'or' is the standard way to merge
    # overlapping shapes into one structure.
    final_clover = gf.boolean(clover_raw, clover_raw, operation="or", layer=layer)
    
    return final_clover

if __name__ == "__main__":
    # Create the component
    device = custom_clover()
    
    # Save the file
    device.write_gds("clover_shape.gds")
    
    print("GDS file 'clover_shape.gds' produced successfully.")
    
    # Display the result
    device.show()