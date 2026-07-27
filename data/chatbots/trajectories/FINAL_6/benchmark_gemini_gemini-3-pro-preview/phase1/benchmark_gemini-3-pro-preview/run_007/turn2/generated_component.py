import gdsfactory as gf
import numpy as np

@gf.cell
def device_star_coupler_curved():
    """
    Creates a four-arm star/clover device with SMOOTH curved sine-profile arms.
    Fixed: Uses a high-resolution path to ensure 'width_type=sine' renders as a curve
    instead of a linear diamond.
    """
    c = gf.Component()
    
    # --- Parameters ---
    # Footprint: 4.7 um -> Radius = 2.35 um
    total_radius = 2.35
    
    # Geometric dimensions
    len_tip = 0.35                       
    len_body = total_radius - len_tip    # 2.0 um
    len_half_body = len_body / 2         # 1.0 um
    
    w_center = 0.25
    w_max = 0.95
    w_tip = 0.2
    
    layer = (1, 0)

    # --- 1. Define Cross Sections ---
    xs_center = gf.cross_section.cross_section(width=w_center, layer=layer)
    xs_max = gf.cross_section.cross_section(width=w_max, layer=layer)
    xs_tip = gf.cross_section.cross_section(width=w_tip, layer=layer)

    # --- 2. Define Transitions ---
    # 'sine' gives the smooth adiabatic expansion/contraction
    trans_expand = gf.path.transition(xs_center, xs_max, width_type='sine')
    trans_contract = gf.path.transition(xs_max, xs_tip, width_type='sine')

    # --- 3. Build Single Arm Component ---
    arm = gf.Component()
    
    # CRITICAL FIX: Create a path with many points.
    # A standard straight path only has 2 points, which creates linear polygon edges.
    # We add 20 points to force the renderer to sample the sine width profile.
    n_points = 20
    points_list = [(i * len_half_body / (n_points - 1), 0) for i in range(n_points)]
    
    path_seg = gf.Path(points_list)
    
    # Extrude Part A: Expansion (Center -> Max) with high resolution path
    part_a = arm << gf.path.extrude_transition(path_seg, trans_expand)
    
    # Extrude Part B: Contraction (Max -> Tip)
    part_b = arm << gf.path.extrude_transition(path_seg, trans_contract)
    part_b.connect("o1", part_a.ports["o2"])
    
    # Part C: Straight Tip (Standard rectangle)
    tip = arm << gf.components.straight(length=len_tip, cross_section=xs_tip)
    tip.connect("o1", part_b.ports["o2"])
    
    # Expose port for rotation
    arm.add_port("o1", port=part_a.ports["o1"])

    # --- 4. Assemble Full Device ---
    for rotation in [0, 90, 180, 270]:
        ref = c << arm
        ref.rotate(rotation)

    return c

if __name__ == "__main__":
    component = device_star_coupler_curved()
    component.write_gds("star_device_curved.gds")
    component.show()