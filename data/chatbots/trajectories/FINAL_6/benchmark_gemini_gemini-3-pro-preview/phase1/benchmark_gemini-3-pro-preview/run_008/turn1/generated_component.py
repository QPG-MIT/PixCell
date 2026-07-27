import gdsfactory as gf

@gf.cell
def flower_device():
    """
    Creates a 4-petal flower device with a 4.7um x 4.7um footprint.
    Uses parametric path transitions to create smooth petal shapes.
    """
    c = gf.Component("flower_device")

    # --- Dimensions ---
    # Total device footprint is 4.7um. Radius = 2.35um.
    radius = 2.35
    
    # The arm consists of: Expand -> Contract -> Stub
    stub_length = 0.35
    petal_body_length = radius - stub_length  # 2.0um
    
    # Split the curved body into two smooth transitions
    l_expand = petal_body_length / 2.0
    l_contract = petal_body_length / 2.0
    
    # Widths derived from image analysis
    w_center = 0.1    # Narrow center point
    w_peak = 1.05     # Widest part of the petal
    w_stub = 0.25     # Width of the rectangular tip

    layer = (1, 0)

    # --- Cross Sections ---
    xs_center = gf.cross_section.cross_section(width=w_center, layer=layer)
    xs_peak = gf.cross_section.cross_section(width=w_peak, layer=layer)
    xs_stub = gf.cross_section.cross_section(width=w_stub, layer=layer)

    # --- Build Single Arm Component ---
    arm = gf.Component("arm_component")
    
    # 1. Expansion Segment (Center -> Peak)
    # 'sine' profile creates a smooth curve with 0 slope at start and end
    t_expand = gf.path.transition(xs_center, xs_peak, width_type='sine')
    path_expand = gf.path.straight(length=l_expand)
    seg_expand = arm << gf.path.extrude_transition(path_expand, t_expand)
    
    # 2. Contraction Segment (Peak -> Tip)
    # Connects smoothly to expansion because 'sine' slope is 0 at the peak
    t_contract = gf.path.transition(xs_peak, xs_stub, width_type='sine')
    path_contract = gf.path.straight(length=l_contract)
    seg_contract = arm << gf.path.extrude_transition(path_contract, t_contract)
    
    # Connect Wide end (o1) of contraction to Wide end (o2) of expansion
    seg_contract.connect("o1", seg_expand.ports["o2"])
    
    # 3. Rectangular Stub
    stub = arm << gf.components.straight(length=stub_length, cross_section=xs_stub)
    # Connect stub to the narrow end (o2) of the contraction segment
    stub.connect("o1", seg_contract.ports["o2"])
    
    # Define the arm's anchor port at the center (start of expansion)
    arm.add_port("o1", port=seg_expand.ports["o1"])

    # --- Assemble Full Device ---
    # Rotate and place 4 arms around the center (0,0)
    for angle in [0, 90, 180, 270]:
        ref = c << arm
        ref.rotate(angle)
        # No move needed; rotation occurs around the origin (0,0) where the arm starts.

    return c

if __name__ == "__main__":
    device = flower_device()
    device.write_gds("flower_device.gds")
    print("GDS file generated successfully: flower_device.gds")