import gdsfactory as gf
import math

@gf.cell
def fork_coupler_adiabatic():
    """
    Recreates the fork coupler using smooth circular arcs for a perfect flare.
    Footprint: 40.0 um x 1.7 um
    """
    c = gf.Component("fork_coupler_adiabatic")
    layer = (1, 0)
    
    # 1. Central Taper (Linear Transition)
    # The central 'tongue' tapers from 0.6um to 0.01um
    t_len = 26.0
    w_start_c = 0.6
    w_end_c = 0.01
    
    taper = c << gf.components.taper(
        length=t_len, 
        width1=w_start_c, 
        width2=w_end_c, 
        layer=layer
    )
    taper.xmin = 0
    taper.y = 0

    # 2. Side Arm Path Construction (Parametric)
    # We use a straight section followed by two arcs forming an S-bend.
    # Radius is large (280um) to ensure a smooth, nearly invisible transition.
    R = 280.0
    angle = 1.55  # Small angle in degrees for a gentle flare
    
    p = gf.path.straight(length=20.0)
    p += gf.path.arc(radius=R, angle=angle)
    p += gf.path.arc(radius=R, angle=-angle)
    
    # Calculate current x to ensure total length is exactly 40.0um
    # dx of S-bend = 2 * R * sin(angle)
    dx_s = 2 * R * math.sin(math.radians(angle))
    remaining_l = 40.0 - (20.0 + dx_s)
    if remaining_l > 0:
        p += gf.path.straight(length=remaining_l)
        
    # Align the path vertically:
    # center_y = (center_width/2) + gap + (arm_width/2)
    # y = 0.3 + 0.05 (gap) + 0.1 (half of 0.2um arm) = 0.45
    p.move((0, 0.45))
    
    # 3. Cross-Section Transition
    # Arms thicken from 0.2um to 0.42um to reach the 1.7um total width boundary.
    # (0.45 start_y + ~0.2 dy from S-bend + 0.21 half_width = 0.86um edge)
    xs1 = gf.cross_section.cross_section(width=0.2, layer=layer)
    xs2 = gf.cross_section.cross_section(width=0.42, layer=layer)
    trans = gf.path.transition(xs1, xs2, width_type='sine')
    
    # 4. Extrude and Assemble
    # Extrude the path into a component and mirror for the bottom arm.
    arm_top = c << gf.path.extrude_transition(p, trans)
    arm_bottom = c << gf.path.extrude_transition(p, trans)
    arm_bottom.mirror_y()

    return c

if __name__ == "__main__":
    # Generate the device
    device = fork_coupler_adiabatic()
    
    # Write to GDS file
    output_name = "fork_coupler_refined.gds"
    device.write_gds(output_name)
    
    # Print verification info
    print(f"GDS file successfully generated: {output_name}")
    print(f"Final Footprint: {device.xsize:.2f} um x {device.ysize:.2f} um")