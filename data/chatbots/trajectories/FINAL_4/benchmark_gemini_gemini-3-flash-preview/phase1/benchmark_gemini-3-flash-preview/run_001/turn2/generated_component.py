import math
import gdsfactory as gf

@gf.cell
def recreate_smooth_waveguides():
    """
    Recreates the curved waveguide geometry using a high-resolution 
    sinusoidal parametric path to ensure maximum smoothness.
    Footprint: 18um x 3um.
    """
    c = gf.Component("smooth_recreation")
    
    # 1. Define physical constraints
    L = 18.0          # Total length
    H = 3.0           # Total height
    w = 0.22          # Waveguide width (matches visual ratio)
    gap_min = 0.08    # Minimum gap at the center waist
    res = 300         # High point density for perfect smoothness
    
    # 2. Calculate centerline bounds
    # At the ends (x=0, x=L), the waveguide edge touches the H/2 boundary.
    y_edge = (H / 2) - (w / 2)
    # At the center (x=L/2), the waveguides approach the center gap.
    y_waist = (gap_min / 2) + (w / 2)
    
    # Parametric constants for: y = A * cos(2*pi*x/L) + offset
    # This creates a peak at 0, a trough at L/2, and a peak at L.
    amplitude = (y_edge - y_waist) / 2.0
    y_offset = (y_edge + y_waist) / 2.0
    
    # 3. Generate the Path points
    # We use Section 3 of the catalog: gf.Path(points)
    pts_top = []
    for i in range(res):
        x = (i / (res - 1)) * L
        # Cosine ensures horizontal tangents at x=0, x=L/2, and x=L
        y = amplitude * math.cos(2 * math.pi * x / L) + y_offset
        pts_top.append((x, y))
    
    # Mirror coordinates for the bottom path
    pts_bot = [(x, -y) for x, y in pts_top]
    
    # 4. Extrude the Paths
    # Using the cross-section system ensures consistent width and layer
    xs = gf.cross_section.cross_section(width=w, layer=(1, 0))
    
    path_top = gf.Path(pts_top)
    path_bot = gf.Path(pts_bot)
    
    c << gf.path.extrude(path_top, cross_section=xs)
    c << gf.path.extrude(path_bot, cross_section=xs)
    
    # 5. Add ports for standard connectivity
    c.add_port("o1", center=(0, y_edge), width=w, orientation=180, layer=(1,0))
    c.add_port("o2", center=(0, -y_edge), width=w, orientation=180, layer=(1,0))
    c.add_port("o3", center=(L, y_edge), width=w, orientation=0, layer=(1,0))
    c.add_port("o4", center=(L, -y_edge), width=w, orientation=0, layer=(1,0))

    return c

if __name__ == "__main__":
    # Build and show the component
    component = recreate_smooth_waveguides()
    component.show()
    
    # Save the output
    component.write_gds("smooth_waveguide_recreation.gds")