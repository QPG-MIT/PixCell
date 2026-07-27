import gdsfactory as gf
import numpy as np

@gf.cell
def star_cross_device():
    """
    Creates a star/flower shaped cross device.
    
    Refined parameters based on visual feedback:
    - Increased petal_width for a "fatter" central body.
    - Decreased stub_width for finer port connections.
    """
    # 1. Define Constraints & Dimensions
    footprint = 4.7
    
    # Tuned parameters to match the target image visually
    stub_width = 0.3      # Narrower ports to match the thin lines in the original
    stub_length = 0.4     # Short rectangular section
    petal_width = 1.8     # Fatter ellipse to create the bulbous flower shape
    
    # 2. Calculate Geometry Parameters
    # The junction is where the rectangular stub meets the curved petal.
    # We define the junction distance from the center.
    junction_dist = footprint / 2 - stub_length
    
    # Ellipse radii setup:
    # rx = radius along the width of the petal (minor radius)
    rx = petal_width / 2
    
    # We calculate ry (major radius) such that the ellipse width exactly matches
    # the stub_width at the specific y = junction_dist.
    # Ellipse Eq: (x/rx)^2 + (y/ry)^2 = 1
    # We know x = stub_width/2 at y = junction_dist.
    
    # Normalized x position (0 to 1) relative to radius
    x_norm = (stub_width / 2) / rx
    
    # Solve for ry
    # (x_norm)^2 + (junction_dist/ry)^2 = 1
    # (junction_dist/ry) = sqrt(1 - x_norm^2)
    # ry = junction_dist / sqrt(1 - x_norm^2)
    
    y_term = np.sqrt(1 - x_norm**2)
    ry = junction_dist / y_term
    
    # 3. Create Primitives
    c = gf.Component()
    
    # Vertical Ellipse
    e_vert = gf.components.ellipse(radii=(rx, ry), layer=(1, 0))
    # Horizontal Ellipse (rotated 90 degrees)
    e_horiz = gf.components.ellipse(radii=(ry, rx), layer=(1, 0))
    
    # Rectangular Stubs
    stub_v = gf.components.rectangle(size=(stub_width, stub_length), layer=(1, 0), centered=True)
    stub_h = gf.components.rectangle(size=(stub_length, stub_width), layer=(1, 0), centered=True)
    
    # 4. Assembly 
    # Add main bodies (references)
    c << e_vert
    c << e_horiz
    
    # Position Stubs
    # Top
    ref_top = c << stub_v
    ref_top.movey(junction_dist + stub_length / 2)
    
    # Bottom
    ref_bot = c << stub_v
    ref_bot.movey(-(junction_dist + stub_length / 2))
    
    # Right
    ref_right = c << stub_h
    ref_right.movex(junction_dist + stub_length / 2)
    
    # Left
    ref_left = c << stub_h
    ref_left.movex(-(junction_dist + stub_length / 2))
    
    # 5. Define Ports
    c.add_port("o1", center=(-footprint/2, 0), width=stub_width, orientation=180, layer=(1,0))
    c.add_port("o2", center=(footprint/2, 0), width=stub_width, orientation=0, layer=(1,0))
    c.add_port("o3", center=(0, footprint/2), width=stub_width, orientation=90, layer=(1,0))
    c.add_port("o4", center=(0, -footprint/2), width=stub_width, orientation=270, layer=(1,0))
    
    return c

# Create and save
device = star_cross_device()
device.write_gds("star_cross_refined.gds")
device.show()