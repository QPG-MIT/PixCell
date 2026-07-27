import gdsfactory as gf
import math
import numpy as np

@gf.cell
def recreate_device_v5():
    """
    Turn 5: High-fidelity reconstruction.
    Optimizes the interaction between the central needle taper and side arm flare.
    Maintains strict 40.0um x 1.7um footprint.
    """
    c = gf.Component("refined_target_v5")
    
    # 1. Constants and Footprint
    L_TOTAL = 40.0
    H_TOTAL = 1.7
    LAYER = (1, 0)
    
    # 2. Central Needle
    # The needle is substantial at the base and tapers very far.
    W_MID_BASE = 0.45
    L_MID_STRAIGHT = 2.0
    L_MID_TAPER = 28.0 
    
    m_xs = gf.cross_section.cross_section(width=W_MID_BASE, layer=LAYER)
    m_straight = c << gf.components.straight(length=L_MID_STRAIGHT, cross_section=m_xs)
    m_taper = c << gf.components.taper(
        length=L_MID_TAPER, 
        width1=W_MID_BASE, 
        width2=0.001,  # Sharp tip
        layer=LAYER
    )
    m_taper.connect("o1", m_straight.ports["o2"])
    
    # 3. Side Arms Parameters
    X_INDENT = 3.5      # Offset from left edge
    W_SIDE_IN = 0.22    # Initial width
    W_SIDE_OUT = 0.56   # Final width
    GAP_INIT = 0.08     # Gap between needle base and side arms
    
    # Calculate Y-offsets for centerlines
    # y_start: centers based on needle base width and initial gap
    y_start = (W_MID_BASE / 2) + GAP_INIT + (W_SIDE_IN / 2)
    # y_final: center such that the outer edge is exactly at H_TOTAL/2
    y_final = (H_TOTAL / 2) - (W_SIDE_OUT / 2)
    dy = y_final - y_start
    
    # 4. Side Arm Path and Extrusion
    length_side = L_TOTAL - X_INDENT
    
    # Flare Timing: The flare starts late (at ~24um relative to arm start)
    x_flare_start = 24.0
    x_flare_end = 34.0
    
    def flare_path(t):
        """t goes from 0 to 1"""
        x = t * length_side
        if x < x_flare_start:
            y = 0
        elif x > x_flare_end:
            y = dy
        else:
            # S-bend transition
            local_t = (x - x_flare_start) / (x_flare_end - x_flare_start)
            y = dy * (1 - math.cos(math.pi * local_t)) / 2
        return (x, y)

    # Generate points for the path
    pts = [flare_path(t) for t in np.linspace(0, 1, 150)]
    side_path = gf.Path(pts)
    
    # Cross-sections for the width transition
    xs_start = gf.cross_section.cross_section(width=W_SIDE_IN, layer=LAYER)
    xs_end = gf.cross_section.cross_section(width=W_SIDE_OUT, layer=LAYER)
    
    # Create width transition (the side arms widen as they flare)
    trans = gf.path.transition(xs_start, xs_end, width_type='linear')
    side_arm_comp = gf.path.extrude_transition(side_path, trans)
    
    # 5. Placement
    # Add Top Arm
    top = c << side_arm_comp
    top.move((X_INDENT, y_start))
    
    # Add Bottom Arm (Symmetrical)
    bot = c << side_arm_comp
    bot.mirror(p1=(0, 0), p2=(1, 0)) # Mirror across X-axis
    bot.move((X_INDENT, -y_start))
    
    return c

if __name__ == "__main__":
    device = recreate_device_v5()
    
    # Verification of constraints
    print(f"Footprint Verification:")
    print(f"Total Length (Target 40.0): {device.dxsize:.3f} um")
    print(f"Total Height (Target 1.7):  {device.dysize:.3f} um")
    
    device.write_gds("device_v5.gds")
    device.show()