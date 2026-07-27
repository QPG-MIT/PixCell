import gdsfactory as gf

@gf.cell
def custom_mmi_geometry():
    """Recreates the geometry of the device using primitives and boolean union."""
    c = gf.Component("mmi_like_device")
    
    # 1. Main central body
    # Spans width 25 and takes up the central 4 units of height
    body = gf.components.rectangle(size=(25.0, 4.0), layer=(1, 0), centered=True)
    
    # 2. Appendages (Arms)
    # We collect all arms in a separate component to union them with the body later
    arms = gf.Component("arms")
    
    # Top output arms (4 evenly spaced)
    # Centers chosen symmetrically at -9, -3, 3, 9 to leave a neat margin on the edges
    for x in [-9.0, -3.0, 3.0, 9.0]:
        # Tapered section (starts at body edge y=2.0, goes up to y=4.0)
        taper = arms << gf.components.taper(length=2.0, width1=3.0, width2=1.0, layer=(1, 0))
        taper.rotate(90).move((x, 2.0))
        
        # Straight section (1.0 tall, placed exactly on top of the taper from y=4.0 to y=5.0)
        straight = arms << gf.components.rectangle(size=(1.0, 1.0), layer=(1, 0), centered=True)
        straight.move((x, 4.5))
        
    # Bottom input arm (1 centered taper)
    # Starts at body edge y=-2.0, goes down to y=-5.0
    taper_bot = arms << gf.components.taper(length=3.0, width1=3.0, width2=1.0, layer=(1, 0))
    taper_bot.rotate(-90).move((0, -2.0))
    
    # 3. Boolean Operations
    # Merge the main body and all arms into a single uninterrupted polygon.
    # This perfectly fulfills the boolean instruction and guarantees it renders as one solid shape.
    merged = gf.boolean(A=body, B=arms, operation="or", layer=(1, 0))
    
    # Add the final monolithic merged geometry to our returning component
    c << merged
    
    return c

if __name__ == "__main__":
    # Create the component
    device = custom_mmi_geometry()
    
    # Save to GDS file
    device.write_gds("custom_mmi_geometry.gds")