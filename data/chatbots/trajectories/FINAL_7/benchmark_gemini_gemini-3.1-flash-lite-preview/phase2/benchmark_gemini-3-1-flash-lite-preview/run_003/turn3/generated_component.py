import gdsfactory as gf

@gf.cell
def racetrack_device():
    c = gf.Component()
    
    # 1. Define cross-section
    # Use a standard strip cross-section.
    xs = gf.cross_section.strip(width=0.5)
    
    # 2. Geometry Parameters
    # We define parameters to ensure the device stays within the [3.0, 5.5] footprint
    straight_len = 1.5
    gap = 1.2
    
    # 3. Create the Straight "Rails"
    # We instantiate these first. They will be our anchor points.
    top_wg = c << gf.components.straight(length=straight_len, cross_section=xs)
    bot_wg = c << gf.components.straight(length=straight_len, cross_section=xs)
    
    # Position them vertically centered around 0
    top_wg.movey(gap / 2)
    bot_wg.movey(-gap / 2)
    
    # 4. Add the Rectangular Features
    # We place these in the middle of the straight sections.
    # Note: Using 'centered=True' puts the center of the rectangle at (0,0)
    rect = gf.components.rectangle(size=(0.6, 0.7), layer=(1, 0), centered=True)
    
    r1 = c << rect
    r1.movey(gap / 2) # Matches the top waveguide
    
    r2 = c << rect
    r2.movey(-gap / 2) # Matches the bottom waveguide
    
    # 5. Route the Connections
    # Instead of manual bends, we use the router to connect the ports.
    # This automatically generates the necessary curves to close the loop.
    
    # Right-side connection
    gf.routing.route_single(c, top_wg.ports["o2"], bot_wg.ports["o2"], cross_section=xs)
    
    # Left-side connection
    gf.routing.route_single(c, bot_wg.ports["o1"], top_wg.ports["o1"], cross_section=xs)
    
    return c

# Generate and save
device = racetrack_device()
device.write_gds("racetrack_device.gds")