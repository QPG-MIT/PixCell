import gdsfactory as gf
import numpy as np

@gf.cell
def directional_coupler_v5_fixed(
    width: float = 0.4,
    gap: float = 0.2,
    coupler_length: float = 80.0,
    bend_dx: float = 15.0,
    ext_length: float = 5.0,
    port_spacing: float = 3.0,
    layer: tuple[int, int] = (1, 0),
) -> gf.Component:
    """
    Directional coupler using Path.smooth to ensure uniform width and 
    precise 120x4 footprint.
    """
    c = gf.Component()
    
    # Coordinate calculations for the top arm
    # Total X = 5 (ext) + 15 (bend) + 80 (coupler) + 15 (bend) + 5 (ext) = 120 um
    y_outer = port_spacing / 2.0
    y_inner = (gap + width) / 2.0
    
    x0 = 0
    x1 = ext_length
    x2 = x1 + bend_dx
    x3 = x2 + coupler_length
    x4 = x3 + bend_dx
    x5 = x4 + ext_length

    # 1. Define Waypoints for the top waveguide
    points = [
        (x0, y_outer),
        (x1, y_outer),
        (x2, y_inner),
        (x3, y_inner),
        (x4, y_outer),
        (x5, y_outer),
    ]
    
    # 2. Create smooth path from waypoints
    # The radius parameter controls the 'softness' of the S-bend
    p = gf.path.smooth(points=points, radius=5.0)
    
    # 3. Define the cross section and extrude
    xs = gf.cross_section.cross_section(width=width, layer=layer)
    top_arm = gf.path.extrude(p, cross_section=xs)
    
    # 4. Create the bottom arm by mirroring the top arm geometry
    # This ensures perfect symmetry
    bot_arm = gf.Component()
    ref_top_for_mirror = bot_arm << top_arm
    ref_top_for_mirror.mirror_y()
    
    # 5. Add arms to the main component
    c << top_arm
    c << bot_arm

    # 6. Define External Ports
    # Extract ports from the top arm
    c.add_port("o1", port=top_arm.ports["o1"]) # Top Left
    c.add_port("o4", port=top_arm.ports["o2"]) # Top Right
    
    # Extract ports from the bottom arm (mirrored component)
    # We need to find the ports on the mirrored reference
    c.add_port("o2", port=ref_top_for_mirror.ports["o1"]) # Bot Left
    c.add_port("o3", port=ref_top_for_mirror.ports["o2"]) # Bot Right

    return c

if __name__ == "__main__":
    # Initialize component
    component = directional_coupler_v5_fixed()
    
    # Verification of constraints
    print(f"Total Length: {component.xsize:.2f} um (Target: 120.0)")
    print(f"Total Height: {component.ysize:.2f} um (Target: < 4.0)")
    
    # Export
    component.write_gds("directional_coupler_v5_fixed.gds")
    component.show()