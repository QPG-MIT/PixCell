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
    R_in = 1.1               # Inner bend radius. Makes bend track uniform width = 0.4
    y_inner_thick = 0.5      # Y-coord of flat central void in the thick section
    x_taper_end = 0.9        # X-coord defining the end of the tapers

    pts = []
    
    # Left Arc (bottom up to top)
    t_left = np.linspace(1.5*np.pi, 0.5*np.pi, 60)
    for t in t_left:
        pts.append((-L_half + R_in * np.cos(t), R_in * np.sin(t)))
        
    # Top Edge (Left taper down to central flat, then taper up to right)
    pts.append((-x_taper_end, y_inner_thick))
    pts.append((x_taper_end, y_inner_thick))
    
    # Right Arc (top down to bottom)
    t_right = np.linspace(0.5*np.pi, -0.5*np.pi, 60)
    for t in t_right:
        pts.append((L_half + R_in * np.cos(t), R_in * np.sin(t)))
        
    # Bottom Edge (Right taper up to central flat, then taper down to left)
    pts.append((x_taper_end, -y_inner_thick))
    pts.append((-x_taper_end, -y_inner_thick))

    holes.add_polygon(pts, layer=layer)

    # --- 3b. Four Rectangular Track Cuts ---
    # Sized to perfectly leave a 0.2 bridge in the middle and 0.1 margins on ends
    w_hole = 0.70
    h_hole = 0.30
    x_hole = 0.45
    
    # Centered at 0.95 (spans Y=0.8 to Y=1.1)
    # Crucially, the top edge of the hole at Y=1.1 EXACTLY aligns with R_in=1.1
    y_hole = 0.95 

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