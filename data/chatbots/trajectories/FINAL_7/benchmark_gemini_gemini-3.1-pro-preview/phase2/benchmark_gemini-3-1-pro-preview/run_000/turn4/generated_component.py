import gdsfactory as gf
import numpy as np

@gf.cell
def parametric_racetrack_device():
    # Main component container
    c = gf.Component("Racetrack_Device")
    layer = (1, 0)

    # ==========================================
    # 1. Main Dimensions (Footprint 3.0 x 5.5)
    # ==========================================
    R_out = 1.5             # Outer radius (Total Height = 3.0)
    L_total = 5.5           # Total width
    L = L_total - 2 * R_out # Straight section length (2.5)
    L_half = L / 2          # 1.25

    # ==========================================
    # 2. Build Positive Geometry (Solid Stadium)
    # ==========================================
    stadium = gf.Component("Solid_Stadium")
    stadium << gf.components.rectangle(size=(L, 2*R_out), centered=True, layer=layer)
    
    ref_circ_left = stadium << gf.components.circle(radius=R_out, layer=layer)
    ref_circ_left.movex(-L_half)
    
    ref_circ_right = stadium << gf.components.circle(radius=R_out, layer=layer)
    ref_circ_right.movex(L_half)

    # ==========================================
    # 3. Build Negative Geometry (Void & Holes)
    # ==========================================
    holes = gf.Component("Holes")

    # --- 3a. Central Void Polygon ---
    R_in = 1.0               # Inner radius at bends (Track width = 0.5)
    y_inner_thick = 0.5      # Y-coord of flat inner edge in thick section
    x_taper_end = 0.9        # X-coord where taper ends and flat thick section begins

    pts = []
    
    # Top edge (left to right)
    pts.append((-L_half, R_in))                 # (-1.25, 1.0)
    pts.append((-x_taper_end, y_inner_thick))   # (-0.9, 0.5)
    pts.append((x_taper_end, y_inner_thick))    # (0.9, 0.5)
    
    # Right arc (top to bottom, bulging right)
    t_right = np.linspace(0.5*np.pi, -0.5*np.pi, 50)
    for t in t_right:
        pts.append((L_half + R_in * np.cos(t), R_in * np.sin(t)))
        
    # Bottom edge (right to left)
    pts.append((x_taper_end, -y_inner_thick))   # (0.9, -0.5)
    pts.append((-x_taper_end, -y_inner_thick))  # (-0.9, -0.5)
    
    # Left arc (bottom to top, bulging left)
    # Crucial Fix: Angles from 1.5*pi to 0.5*pi bulge leftwards
    t_left = np.linspace(1.5*np.pi, 0.5*np.pi, 50)
    for t in t_left[:-1]: # Skip the exact last point to cleanly avoid a duplicate start point
        pts.append((-L_half + R_in * np.cos(t), R_in * np.sin(t)))

    holes.add_polygon(pts, layer=layer)

    # --- 3b. Four Rectangular Track Cuts ---
    w_hole = 0.55
    h_hole = 0.40
    x_hole = 0.40
    y_hole = 1.00 # Centered vertically in the thicker track segment (0.5 to 1.5)

    cut_comp = gf.components.rectangle(size=(w_hole, h_hole), centered=True, layer=layer)
    
    # Top Left
    ref_c1 = holes << cut_comp
    ref_c1.move((-x_hole, y_hole))
    
    # Top Right
    ref_c2 = holes << cut_comp
    ref_c2.move((x_hole, y_hole))
    
    # Bottom Left
    ref_c3 = holes << cut_comp
    ref_c3.move((-x_hole, -y_hole))
    
    # Bottom Right
    ref_c4 = holes << cut_comp
    ref_c4.move((x_hole, -y_hole))

    # ==========================================
    # 4. Final Boolean Subtraction
    # ==========================================
    final_shape = gf.boolean(A=stadium, B=holes, operation='not', layer=layer)
    c << final_shape

    return c

if __name__ == "__main__":
    device = parametric_racetrack_device()
    device.write_gds("device.gds")