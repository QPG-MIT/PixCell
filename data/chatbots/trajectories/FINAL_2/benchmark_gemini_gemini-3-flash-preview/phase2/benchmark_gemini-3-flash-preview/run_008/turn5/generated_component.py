import gdsfactory as gf

@gf.cell
def finger_unit(taper_length=2.0, total_height=5.0, width_base=2.4, width_tip=1.1):
    """
    Creates a single finger with a tapered base and a long straight tip.
    """
    c = gf.Component()
    layer = (1, 0)
    
    # 1. Tapered base 
    tbase = c << gf.components.taper(
        length=taper_length, 
        width1=width_base, 
        width2=width_tip, 
        layer=layer
    )
    tbase.rotate(90) # Vertical orientation
    
    # 2. Straight top section
    straight_height = total_height - taper_length
    ttip = c << gf.components.rectangle(
        size=(width_tip, straight_height), 
        layer=layer, 
        centered=False
    )
    # Position: center x on 0, bottom y on top of taper
    ttip.move((-width_tip/2, taper_length))
    
    return c

@gf.cell
def recreate_device():
    """
    Reconstructs the 4-to-1 coupler device based on Turn 5 analysis.
    Footprint: 25um (W) x 10um (H)
    """
    c = gf.Component("improved_fanout_v5")
    layer = (1, 0)
    
    # Vertical Budget (Total = 10.0 um):
    # Bottom Stub:  1.5 um (y=0.0 to 1.5)
    # Main Body:    3.5 um (y=1.5 to 5.0)
    # Top Fingers:  5.0 um (y=5.0 to 10.0)
    
    body_h = 3.5
    body_w = 25.0
    stub_h = 1.5
    finger_h = 5.0
    
    # 1. Main Body
    body = c << gf.components.rectangle(
        size=(body_w, body_h), 
        layer=layer, 
        centered=True
    )
    body.movey(stub_h + body_h/2) 
    
    # 2. Top Fingers (4 units)
    # Spacing adjusted for a wider distribution across the 25um body
    f_unit = finger_unit(taper_length=2.0, total_height=finger_h, width_base=2.4, width_tip=1.1)
    finger_x_positions = [-9.5, -3.3, 3.3, 9.5]
    
    for x in finger_x_positions:
        f_ref = c << f_unit
        f_ref.x = x
        f_ref.ymin = body.ymax - 0.02 # Small overlap for GDS integrity
        
    # 3. Bottom Stub
    # Wider base at the body to match visual weight
    stub = c << gf.components.taper(
        length=stub_h, 
        width1=3.8, 
        width2=1.2, 
        layer=layer
    )
    stub.rotate(-90) 
    stub.x = 0
    stub.ymax = body.ymin + 0.02 # Small overlap
    
    return c

if __name__ == "__main__":
    device = recreate_device()
    
    # Export and Verify
    filename = "refined_coupler_v5.gds"
    device.write_gds(filename)
    
    print(f"File Saved: {filename}")
    print(f"Dimensions: {device.xsize:.2f}um x {device.ysize:.2f}um")
    # device.show()