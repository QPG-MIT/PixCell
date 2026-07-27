import gdsfactory as gf

@gf.cell
def tapered_waveguide():
    c = gf.Component()
    
    # Define cross-section for the waveguide
    # Set radius_min to match the bend radius we'll use
    xs = gf.cross_section.cross_section(
        width=0.5, 
        layer=(1, 0),
        radius=1.0  # This is the min bend radius allowed
    )
    
    # Create a straight waveguide segment (start of device)
    straight = c << gf.components.straight(length=2.0, cross_section=xs)
    
    # Create a 90-degree Euler bend with radius = 1.0 (satisfies constraint)
    bend = c << gf.components.bend_euler(radius=1.0, angle=90, cross_section=xs)
    
    # Connect the bend to the straight segment
    bend.connect("o1", straight.ports["o2"])
    
    # Create a taper that goes from 0.5 to 0.1 width to form the pointed end
    taper = c << gf.components.taper(length=2.5, width1=0.5, width2=0.1)
    
    # Connect the taper to the bend
    taper.connect("o1", bend.ports["o2"])
    
    # Add ports for connectivity
    c.add_port("o1", port=straight.ports["o1"])
    c.add_port("o2", port=taper.ports["o2"])
    
    # Optional: check footprint (should be ~3.0 x 5.5 um)
    # We can adjust lengths if needed to fit constraint exactly
    # Current approx: straight (2.0) + bend (1.0 radius, so ~1.0 in y) + taper (2.5) → total ~5.5 in x, ~3.0 in y
    
    return c

# Create the device
device = tapered_waveguide()
device.write_gds("tapered_waveguide.gds")