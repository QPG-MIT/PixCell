import gdsfactory as gf

@gf.cell
def device_cross_flower():
    c = gf.Component()

    # --- Dimensions ---
    # Total footprint constraint: 4.7um x 4.7um
    total_span = 4.7
    radius = total_span / 2.0  # 2.35um
    
    # Geometry estimates derived from image
    tip_length = 0.35
    petal_length = radius - tip_length # 2.0um
    
    width_center = 1.0  # Width at the center intersection
    width_tip = 0.2     # Width at the narrow tip
    
    layer_wg = (1, 0)

    # --- Definitions ---
    # 1. Cross Sections
    xs_center = gf.cross_section.cross_section(width=width_center, layer=layer_wg)
    xs_tip = gf.cross_section.cross_section(width=width_tip, layer=layer_wg)

    # 2. Parametric Petal Construction
    # We use a 'sine' transition to create the smooth, bulbous taper shape.
    # This varies the width from thick (center) to thin (tip) smoothly.
    transition = gf.path.transition(xs_center, xs_tip, width_type='sine')
    path_petal = gf.path.straight(length=petal_length)
    
    # Extrude the path with the variable width transition
    petal_component = gf.path.extrude_transition(path_petal, transition)
    
    # 3. Tip Construction
    # A simple straight segment for the end
    tip_component = gf.components.straight(length=tip_length, cross_section=xs_tip)

    # --- Assembly ---
    # Create 4 arms rotated around the center
    for i, angle in enumerate([0, 90, 180, 270]):
        # Add the tapered petal
        # The path starts at (0,0) by default, so rotating it pivots around the center
        ref_petal = c << petal_component
        ref_petal.rotate(angle)
        
        # Add the straight tip
        ref_tip = c << tip_component
        
        # Connect the start of the tip ("o1") to the end of the petal ("o2")
        ref_tip.connect("o1", ref_petal.ports["o2"])
        
        # Expose the outer port for connectivity
        c.add_port(f"o{i+1}", port=ref_tip.ports["o2"])

    return c

if __name__ == "__main__":
    # Generate and save the GDS file
    device = device_cross_flower()
    device.write_gds("device_cross_flower.gds")
    
    # Print dimensions to verify against constraints
    print(f"Device Footprint: {device.size_info.width:.2f} um x {device.size_info.height:.2f} um")