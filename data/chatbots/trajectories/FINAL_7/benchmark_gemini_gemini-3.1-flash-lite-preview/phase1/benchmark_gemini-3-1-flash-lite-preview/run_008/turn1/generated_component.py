import gdsfactory as gf

@gf.cell
def create_device():
    c = gf.Component()
    
    # 1. Define Cross Section (width of the lines)
    # Using 0.4um as a reasonable thickness for the structures
    xs = gf.cross_section.cross_section(width=0.4, layer=(1, 0))

    # 2. Outer Loop (Stadium shape)
    # Use path construction to ensure parametric accuracy
    # A racetrack loop: 2 straight lines and 2 semicircles
    path = gf.Path()
    path.append(gf.path.straight(length=2.5))              # Top straight
    path.append(gf.path.arc(radius=1.5, angle=180))       # Right arc
    path.append(gf.path.straight(length=2.5))              # Bottom straight
    path.append(gf.path.arc(radius=1.5, angle=180))       # Left arc
    
    # Extrude path to create the outer ring
    outer_ring = c << gf.path.extrude(path, cross_section=xs)
    
    # Align the racetrack center to (0,0)
    outer_ring.center = (0, 0)

    # 3. Inner Rectangles
    # Placing two rectangles at x = -0.75 and x = +0.75
    rect_size = (0.8, 1.0)
    inner1 = c << gf.components.rectangle(size=rect_size, layer=(1, 0), centered=True)
    inner2 = c << gf.components.rectangle(size=rect_size, layer=(1, 0), centered=True)
    
    inner1.movex(-0.75)
    inner2.movex(0.75)

    # 4. Connecting Bridges
    # Create 4 straight waveguides to connect inner rects to the outer loop
    # Length of bridges = (Total_Height - Inner_Height) / 2 = (3.0 - 1.0) / 2 = 1.0
    bridge_length = 1.0
    
    # Helper to add bridges
    def add_bridge(x_pos, y_pos):
        bridge = c << gf.components.straight(length=bridge_length, cross_section=xs)
        bridge.rotate(90)
        bridge.move((x_pos, y_pos))
        return bridge

    # Positions based on inner rect placement
    # Top/Bottom of inner blocks is at y = +/- 0.5
    add_bridge(x_pos=-0.75, y_pos=1.0)  # Top-left bridge
    add_bridge(x_pos=-0.75, y_pos=-1.0) # Bottom-left bridge
    add_bridge(x_pos=0.75, y_pos=1.0)   # Top-right bridge
    add_bridge(x_pos=0.75, y_pos=-1.0)  # Bottom-right bridge

    return c

# Generate and save the device
if __name__ == "__main__":
    device = create_device()
    device.show() # Opens KLayout
    device.write_gds("racetrack_device.gds")