import gdsfactory as gf

@gf.cell
def recreate_device():
    """
    Recreates the device geometry from the image using parametric primitives.
    Total Footprint: 25um (width) x 10um (height)
    """
    c = gf.Component("device_recreation")
    layer = (1, 0)

    # 1. Define vertical dimensions (Sum = 10um)
    # Total Height = Bottom (1) + Body (6) + Top (3) = 10um
    body_h = 6.0
    top_h = 3.0    # Split into 1.5 taper + 1.5 straight
    bot_h = 1.0
    
    # Define horizontal dimensions (Max width = 25um)
    body_w = 25.0
    finger_base_w = 2.0
    finger_tip_w = 0.8
    stub_base_w = 3.0
    stub_tip_w = 1.5

    # 2. Create the main central body
    # Center at (0,0), so Y spans -3 to +3
    body = c << gf.components.rectangle(size=(body_w, body_h), layer=layer, centered=True)

    # 3. Create the top finger assembly (4 units)
    # We define a single finger component first
    finger = gf.Component("finger_unit")
    
    # Finger Part A: Taper (base to tip)
    ft = finger << gf.components.taper(
        length=1.5, 
        width1=finger_base_w, 
        width2=finger_tip_w, 
        layer=layer
    )
    ft.rotate(90) # Orient Up
    
    # Finger Part B: Straight tip
    fs = finger << gf.components.rectangle(
        size=(finger_tip_w, 1.5), 
        layer=layer,
        centered=True
    )
    # Position straight tip on top of taper (taper ends at y=1.5, rect center at 1.5 + 0.75)
    fs.movey(2.25)

    # Place 4 fingers on the top edge of the body (y = 3.0)
    # X-positions spaced to look like the image
    x_coords = [-8.5, -3.0, 3.0, 8.5]
    for x in x_coords:
        f_ref = c << finger
        f_ref.move((x, body_h / 2))

    # 4. Create the bottom stub
    # Taper pointing down
    stub = gf.Component("bottom_stub")
    st = stub << gf.components.taper(
        length=bot_h, 
        width1=stub_base_w, 
        width2=stub_tip_w, 
        layer=layer
    )
    st.rotate(-90) # Orient Down
    
    s_ref = c << stub
    s_ref.movey(-body_h / 2) # Attach to bottom edge (y = -3.0)

    return c

if __name__ == "__main__":
    # Create the component
    device = recreate_device()
    
    # Write to GDS file (This ensures a file is produced in the current folder)
    filename = "recreated_device.gds"
    device.write_gds(filename)
    
    # Verification output
    # Note: Using properties xsize/ysize which are standard in GDSFactory Component
    print(f"Success: GDS file '{filename}' has been produced.")
    print(f"Device Footprint: {device.xsize:.1f}um x {device.ysize:.1f}um")
    
    # Optional: Try to open in KLayout if available
    try:
        device.show()
    except Exception:
        print("Note: 'show()' failed. Please open 'recreated_device.gds' in KLayout manually.")