import numpy as np
import gdsfactory as gf

@gf.cell
def patterned_racetrack_resonator():
    """
    Constructs a patterned racetrack resonator matching the chain-link slotted profile.
    Uses discrete polygon definitions to guarantee stable boolean operations and exact 
    dimension control matching the 5.5 x 3.0 um footprint.
    """
    c = gf.Component("patterned_racetrack")
    LAYER = (1, 0)
    
    # ==========================================
    # 1. OUTER SOLID RACETRACK POLYGON
    # ==========================================
    # Footprint constraint: 5.5 x 3.0 um
    # Straight length = 2.5 um (x from -1.25 to 1.25)
    # Outer radius = 1.5 um
    c_outer = gf.Component("outer_solid")
    pts_outer = []
    
    # Right semi-circle
    for a in np.linspace(-np.pi/2, np.pi/2, 65):
        pts_outer.append((1.25 + 1.5 * np.cos(a), 1.5 * np.sin(a)))
        
    # Left semi-circle
    for a in np.linspace(np.pi/2, 3*np.pi/2, 65):
        pts_outer.append((-1.25 + 1.5 * np.cos(a), 1.5 * np.sin(a)))
        
    c_outer.add_polygon(pts_outer, layer=LAYER)

    # ==========================================
    # 2. INNER VOIDS (Main Carve-out & Slots)
    # ==========================================
    c_voids = gf.Component("all_voids")
    
    # --- A. Main Central Void ---
    pts_inner = []
    
    # Right inner semi-circle (Radius 1.0)
    for a in np.linspace(-np.pi/2, np.pi/2, 65):
        pts_inner.append((1.25 + 1.0 * np.cos(a), 1.0 * np.sin(a)))
        
    # Top taper leading into the narrowed central gap
    pts_inner.append((0.65, 0.3))
    pts_inner.append((-0.65, 0.3))
    
    # Left inner semi-circle
    for a in np.linspace(np.pi/2, 3*np.pi/2, 65):
        pts_inner.append((-1.25 + 1.0 * np.cos(a), 1.0 * np.sin(a)))
        
    # Bottom narrow central gap and taper
    pts_inner.append((-0.65, -0.3))
    pts_inner.append((0.65, -0.3))
    
    c_voids.add_polygon(pts_inner, layer=LAYER)

    # --- B. Rectangular Slots (Chain Links) ---
    # Top solid rail spans y=0.3 to y=1.5 (center y=0.9)
    # Bottom solid rail spans y=-1.5 to y=-0.3 (center y=-0.9)
    # Narrow straight region spans x=-0.65 to x=0.65 (total length 1.3)
    # We place two slots in each rail, length 0.55 each, leaving a 0.2um center gap.
    
    def get_rect_pts(cx, cy, w, h):
        return [
            (cx - w/2, cy - h/2),
            (cx + w/2, cy - h/2),
            (cx + w/2, cy + h/2),
            (cx - w/2, cy + h/2)
        ]

    slot_w, slot_h = 0.55, 0.4
    slot_centers = [
        (-0.375, 0.9),  # Top-left
        (0.375, 0.9),   # Top-right
        (-0.375, -0.9), # Bottom-left
        (0.375, -0.9)   # Bottom-right
    ]
    
    for cx, cy in slot_centers:
        slot_pts = get_rect_pts(cx, cy, slot_w, slot_h)
        c_voids.add_polygon(slot_pts, layer=LAYER)

    # ==========================================
    # 3. FINAL BOOLEAN SUBTRACTION
    # ==========================================
    # Subtracts all nested void polygon structures from the solid outer racetrack
    final_geom = gf.boolean(A=c_outer, B=c_voids, operation="not", layer=LAYER)
    
    c << final_geom
    
    return c


if __name__ == "__main__":
    device = patterned_racetrack_resonator()
    device.show() # Display output if rendering locally
    device.write_gds("patterned_racetrack_resonator.gds")