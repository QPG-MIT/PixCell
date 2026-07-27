import gdsfactory as gf

@gf.cell
def recreated_device_v3():
    """
    Refined version of the four-petal device.
    - Slimmer, more organic petals.
    - Narrower stubs for accurate visual matching.
    - Smooth central junction.
    - Total Footprint: 4.7um x 4.7um.
    """
    c = gf.Component("device_final_v3")
    layer = (1, 0)

    # --- 1. Dimensions (Half-span = 2.35um) ---
    # The petals are represented by ellipses. 
    # To get the 'almond' shape, we use a major radius that slightly 
    # undershoots the edge, letting the stub take over.
    petal_major_r = 2.1    
    petal_minor_r = 0.72   
    
    # Stub dimensions
    stub_w = 0.32          # Slightly narrower than previous attempt
    stub_l = 0.6           # Length of the stub
    
    # Calculate stub position: 
    # Must end at 2.35um. Center is 2.35 - (length/2)
    stub_pos = 2.35 - (stub_l / 2) # 2.05um

    # --- 2. Create Primitives ---
    # Petal Ellipses
    e_h = gf.components.ellipse(radii=(petal_major_r, petal_minor_r), layer=layer)
    e_v = gf.components.ellipse(radii=(petal_minor_r, petal_major_r), layer=layer)
    
    # Central hub to smooth the intersection
    center_hub = gf.components.circle(radius=0.6, layer=layer)
    
    # Rectangular stub templates
    rect_h = gf.components.rectangle(size=(stub_l, stub_w), layer=layer, centered=True)
    rect_v = gf.components.rectangle(size=(stub_w, stub_l), layer=layer, centered=True)

    # --- 3. Assembly ---
    temp = gf.Component("temp_assembly")
    temp << e_h
    temp << e_v
    temp << center_hub

    # Add the 4 stubs at the cardinal points
    s_right = temp << rect_h
    s_right.movex(stub_pos)

    s_left = temp << rect_h
    s_left.movex(-stub_pos)

    s_top = temp << rect_v
    s_top.movey(stub_pos)

    s_bottom = temp << rect_v
    s_bottom.movey(-stub_pos)

    # --- 4. Final Processing ---
    # Merge everything into a single silhouette.
    # We apply a very small geometry offset (dilation/erosion) 
    # to naturally smooth the joints between ellipses and rectangles.
    merged = gf.boolean(A=temp, B=temp, operation="or", layer=layer)
    
    # Optional: subtle corner rounding for that lithographic 'organic' look
    # final_geom = gf.geometry.offset(merged, distance=0.01, layer=layer) # Dilate
    # final_geom = gf.geometry.offset(final_geom, distance=-0.01, layer=layer) # Erode
    
    c.add_ref(merged)

    return c

if __name__ == "__main__":
    # Generate the component
    device = recreated_device_v3()
    
    # Save to GDS file
    filename = "recreated_device_v3.gds"
    device.write_gds(filename)
    
    print(f"Success! GDS file saved as: {filename}")
    # device.show() # Uncomment to view in KLayout