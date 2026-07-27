import gdsfactory as gf

@gf.cell
def custom_mmi_geometry():
    """Recreates the geometry of the device using precisely scaled primitives and safe boolean union."""
    c = gf.Component("mmi_improved_v2")
    
    # Create temporary components to hold the parts before boolean union
    body_comp = gf.Component("body_temp")
    arms_comp = gf.Component("arms_temp")
    
    # 1. Main central body
    # Occupies 4.5 units of the total 10 height.
    # Centered horizontally, vertically shifted to span y = -3.5 to y = 1.0
    body = body_comp << gf.components.rectangle(size=(25.0, 4.5), layer=(1, 0), centered=True)
    body.move((0, -1.25))
    
    # 2. Appendages (Top Arms)
    # Positions calculated for 4 arms of base width 3.2 and 5 equal gaps of 2.44
    x_positions = [-8.46, -2.82, 2.82, 8.46]
    
    for x in x_positions:
        # Tapered section
        # Starts safely inside the body at y=0.9 (0.1 overlap) and ends at y=2.5
        taper = arms_comp << gf.components.taper(length=1.6, width1=3.2, width2=1.6, layer=(1, 0))
        taper.rotate(90).move((x, 0.9))
        
        # Straight section
        # Starts inside the taper at y=2.4 (0.1 overlap) and goes exactly to the y=5.0 top boundary
        straight = arms_comp << gf.components.rectangle(size=(1.6, 2.6), layer=(1, 0), centered=True)
        straight.move((x, 3.7))  # center is at (2.4 + 5.0) / 2 = 3.7
        
    # 3. Bottom input arm
    # Starts safely inside the body at y=-3.4 (0.1 overlap) and tapers exactly down to the y=-5.0 boundary
    bot_taper = arms_comp << gf.components.taper(length=1.6, width1=3.2, width2=1.0, layer=(1, 0))
    bot_taper.rotate(-90).move((0, -3.4))
    
    # 4. Boolean Operation
    # Merge the safely overlapping segments into a single, seamless, monolithic polygon
    merged = gf.boolean(A=body_comp, B=arms_comp, operation="or", layer=(1, 0))
    
    # Add to final returning component
    c << merged
    
    return c

if __name__ == "__main__":
    # Create the component
    device = custom_mmi_geometry()
    
    # Save to GDS file
    device.write_gds("custom_mmi_geometry.gds")