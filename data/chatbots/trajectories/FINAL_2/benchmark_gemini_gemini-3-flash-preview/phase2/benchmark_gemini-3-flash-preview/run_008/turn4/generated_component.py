import gdsfactory as gf

@gf.cell
def finger_component():
    """
    Creates a single finger for the fan-out structure.
    Consists of a short tapered transition and a long straight section.
    Total height: 4.5um
    """
    c = gf.Component()
    layer = (1, 0)
    
    # 1. Tapered base (1.2um height)
    # Transitions from 2.2um (where it hits the body) to 1.5um
    tbase = c << gf.components.taper(
        length=1.2, 
        width1=2.2, 
        width2=1.5, 
        layer=layer
    )
    tbase.rotate(90) # Now vertical, extending from y=0 to y=1.2
    
    # 2. Straight tip (3.3um height)
    # Matches the 1.5um width of the taper end
    ttip = c << gf.components.rectangle(
        size=(1.5, 3.3), 
        layer=layer, 
        centered=False
    )
    # Position exactly on top of the taper
    ttip.move(( -0.75, 1.2 )) # Center X at 0, bottom Y at 1.2
    
    return c

@gf.cell
def recreate_device():
    """
    Reconstructs the 4-to-1 coupler device.
    Footprint: 25um (W) x 10um (H)
    """
    c = gf.Component("connected_fanout_device")
    layer = (1, 0)
    
    # Vertical Budget (Total = 10.0 um):
    # Bottom Stub:  1.5 um (y=0.0 to 1.5)
    # Main Body:    4.0 um (y=1.5 to 5.5)
    # Top Fingers:  4.5 um (y=5.5 to 10.0)
    
    # 1. Main Body
    # Centered at (0, 3.5) so it spans y=1.5 to y=5.5
    body = c << gf.components.rectangle(
        size=(25.0, 4.0), 
        layer=layer, 
        centered=True
    )
    body.movey(3.5) 
    
    # 2. Top Fingers (4 units)
    # Using specific x-offsets to match visual distribution
    f_unit = finger_component()
    finger_x_positions = [-9.5, -3.2, 3.2, 9.5]
    
    for x in finger_x_positions:
        f_ref = c << f_unit
        f_ref.x = x
        f_ref.ymin = body.ymax - 0.01 # Slight overlap to ensure connectivity
        
    # 3. Bottom Stub
    # Single taper transitioning from 3.0um at body to 1.5um at bottom
    stub = c << gf.components.taper(
        length=1.5, 
        width1=3.0, 
        width2=1.5, 
        layer=layer
    )
    stub.rotate(-90) # Vertical, wide part at the top
    stub.x = 0
    stub.ymax = body.ymin + 0.01 # Slight overlap to ensure connectivity
    
    return c

if __name__ == "__main__":
    # Generate the device
    device = recreate_device()
    
    # Save GDS
    filename = "target_matched_device_v4.gds"
    device.write_gds(filename)
    
    print(f"Success: '{filename}' generated.")
    print(f"Footprint Verification: {device.xsize}um x {device.ysize}um")
    
    # To view: device.show()