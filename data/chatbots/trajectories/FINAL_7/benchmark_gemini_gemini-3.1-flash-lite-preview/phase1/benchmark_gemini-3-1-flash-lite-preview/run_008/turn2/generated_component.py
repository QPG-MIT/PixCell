import gdsfactory as gf

@gf.cell
def internal_structure():
    """Creates the 'H' shaped internal geometry."""
    c = gf.Component()
    # Vertical bar of the H
    c << gf.components.rectangle(size=(0.4, 2.2), centered=True)
    # Horizontal crossbar of the H
    c << gf.components.rectangle(size=(1.2, 0.6), centered=True)
    return c

@gf.cell
def racetrack():
    """Creates the outer stadium loop."""
    c = gf.Component()
    # Stadium dimensions based on your image
    radius = 1.5
    straight_len = 2.5
    
    # Path construction for the stadium
    p = gf.Path()
    p.append(gf.path.straight(length=straight_len))
    p.append(gf.path.arc(radius=radius, angle=180))
    p.append(gf.path.straight(length=straight_len))
    p.append(gf.path.arc(radius=radius, angle=180))
    
    # Extrude path
    c << gf.path.extrude(p, cross_section=gf.cross_section.cross_section(width=0.4, layer=(1, 0)))
    return c

@gf.cell
def final_device():
    c = gf.Component()
    
    # 1. Add the Racetrack
    # The racetrack is centered at (0,0) by default
    c << racetrack()
    
    # 2. Add two internal structures
    # We assign them to variables 's1' and 's2' (these are references)
    s1 = c << internal_structure()
    s2 = c << internal_structure()
    
    # 3. Position the references
    # Since we are modifying the REFERENCE, not the CELL, this will not trigger the lock error
    s1.movex(-0.8)
    s2.movex(0.8)
    
    return c

# Generate the device
if __name__ == "__main__":
    device = final_device()
    device.show()  # Opens KLayout
    device.write_gds("racetrack_device.gds")