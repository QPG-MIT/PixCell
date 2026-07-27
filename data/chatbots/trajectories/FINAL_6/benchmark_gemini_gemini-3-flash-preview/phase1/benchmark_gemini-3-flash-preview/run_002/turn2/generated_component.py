import gdsfactory as gf

@gf.cell
def recreated_device_v2():
    """
    Recreates the device with seamless transitions between petals and stubs.
    Total Footprint: 4.7um x 4.7um (Radius = 2.35um).
    """
    c = gf.Component("device_final")
    layer = (1, 0)

    # --- 1. Define Dimensions ---
    # Total span must be 2.35um from center.
    petal_major_r = 2.05    # Ellipse semi-major axis
    petal_minor_r = 0.75    # Ellipse semi-minor axis (gives the 'bulge')
    
    stub_w = 0.4            # Width of the rectangular leads
    stub_l = 0.65           # Length of the rectangular leads
    
    # Calculate position to ensure a 0.35um overlap to eliminate gaps
    # Stub ends at 2.35um. Center is at 2.35 - (stub_l / 2)
    stub_center_pos = 2.35 - (stub_l / 2) # 2.025um

    # --- 2. Create Primitives ---
    # Horizontal and Vertical Ellipses for the body
    e_h = gf.components.ellipse(radii=(petal_major_r, petal_minor_r), layer=layer)
    e_v = gf.components.ellipse(radii=(petal_minor_r, petal_major_r), layer=layer)
    
    # Rectangular stub templates
    rect_h = gf.components.rectangle(size=(stub_l, stub_w), layer=layer, centered=True)
    rect_v = gf.components.rectangle(size=(stub_w, stub_l), layer=layer, centered=True)

    # --- 3. Assembly into a temporary container ---
    temp = gf.Component("temp_assembly")
    temp << e_h
    temp << e_v

    # Add and position the 4 stubs
    s_right = temp << rect_h
    s_right.movex(stub_center_pos)

    s_left = temp << rect_h
    s_left.movex(-stub_center_pos)

    s_top = temp << rect_v
    s_top.movey(stub_center_pos)

    s_bottom = temp << rect_v
    s_bottom.movey(-stub_center_pos)

    # --- 4. Boolean Operation ---
    # This merges all overlapping parts into one single silhouette, 
    # removing the internal lines and the gaps seen in the previous version.
    merged = gf.boolean(A=temp, B=temp, operation="or", layer=layer)
    c.add_ref(merged)

    return c

if __name__ == "__main__":
    # Generate the component
    device = recreated_device_v2()
    
    # Save to GDS file
    filename = "recreated_device_v2.gds"
    device.write_gds(filename)
    
    print(f"Success! GDS file saved as: {filename}")
    # device.show() # Uncomment to view in KLayout