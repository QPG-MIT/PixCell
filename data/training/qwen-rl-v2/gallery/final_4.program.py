import gdsfactory as gf

# Physical footprint parameters
X_LENGTH = 18.0
Y_WIDTH = 3.0
WAVE_AMPLITUDE = 1.0

@gf.cell
def device():
    c = gf.Component()
    
    xs = gf.cross_section.cross_section(width=1.0, layer=(1, 0))
    
    # Create upper wave path
    points_upper = [(0, Y_WIDTH/2), (X_LENGTH/2, 0), (X_LENGTH, Y_WIDTH/2)]
    path_upper = gf.path.smooth(points_upper, radius=4.0)
    comp_upper = gf.path.extrude(path_upper, cross_section=xs)
    
    # Create lower wave path  
    points_lower = [(0, -Y_WIDTH/2), (X_LENGTH/2, 0), (X_LENGTH, -Y_WIDTH/2)]
    path_lower = gf.path.smooth(points_lower, radius=4.0)
    comp_lower = gf.path.extrude(path_lower, cross_section=xs)
    
    c << comp_upper
    c << comp_lower
    
    return c

if __name__ == "__main__":
    d = device()
    d.write_gds("device.gds")