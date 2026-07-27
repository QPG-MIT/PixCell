import gdsfactory as gf

@gf.cell
def finger_component():
    """
    Creates a single finger with a wide tapered base and a thick straight tip.
    Total height: 4.0um (1.5um taper + 2.5um straight)
    """
    c = gf.Component()
    layer = (1, 0)
    
    # 1. Tapered base (1.5um height)
    # Transitions from 3.2um base to 1.8um tip
    tbase = c << gf.components.taper(
        length=1.5, 
        width1=3.2, 
        width2=1.8, 
        layer=layer
    )
    tbase.rotate(90)
    # Taper is created centered at (0.75, 0) then rotated to be centered at (0, 0.75)
    # We move it so the base sits at y=0
    tbase.movey(0.75)
    
    # 2. Straight thick tip (2.5um height)
    # Matches the end of the taper (1.8um)
    ttip = c << gf.components.rectangle(
        size=(1.8, 2.5), 
        layer=layer, 
        centered=True
    )
    # Position on top of the taper (which ends at y=1.5)
    # Rectangle center is at 1.5 + 1.25 = 2.75
    ttip.movey(2.75)
    
    return c

@gf.cell
def recreate_device():
    """
    Reconstructs the device with accurate proportions and blocky features.
    Total Footprint Constraint: 25um (width) x 10um (height)
    """
    c = gf.Component("final_refined_device")
    layer = (1, 0)
    
    # Vertical Budget (Total = 10.0 um):
    # Bottom Stub:  1.5 um (y=0.0 to 1.5)
    # Main Body:    4.5 um (y=1.5 to 6.0)
    # Top Fingers:  4.0 um (y=6.0 to 10.0)
    
    # 1. Main Body (Rectangle)
    # Centered horizontally at 0, vertically positioned above the stub
    body = c << gf.components.rectangle(
        size=(25.0, 4.5), 
        layer=layer, 
        centered=True
    )
    body.movey(1.5 + 2.25) # Bottom at 1.5, height 4.5
    
    # 2. Top Fingers (4 units)
    # Distributed widely across the 25um width
    f_unit = finger_component()
    # Positions chosen to match the coverage in the target image
    finger_x_positions = [-9.5, -3.2, 3.2, 9.5]
    for x in finger_x_positions:
        f_ref = c << f_unit
        f_ref.move((x, 6.0)) # Attach to the top edge of the body
        
    # 3. Bottom Stub (Blunt taper)
    # Transitions from 2.8um body contact to 1.4um tip
    stub = c << gf.components.taper(
        length=1.5, 
        width1=2.8, 
        width2=1.4, 
        layer=layer
    )
    stub.rotate(-90)
    # Positioned at the bottom (y=0 to 1.5)
    stub.movey(0.75)
    
    return c

if __name__ == "__main__":
    # Generate the device
    device = recreate_device()
    
    # Output file
    filename = "target_matched_device.gds"
    device.write_gds(filename)
    
    # Verification
    print(f"Success: '{filename}' generated.")
    print(f"Final Footprint: {device.xsize:.1f}um (W) x {device.ysize:.1f}um (H)")
    
    # Visualization attempt
    try:
        device.show()
    except Exception:
        print("Note: GDS viewing depends on local environment (e.g., KLayout).")