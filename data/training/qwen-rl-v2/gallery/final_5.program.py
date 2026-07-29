import gdsfactory as gf

@gf.cell
def device():
    c = gf.Component()
    
    # Define parameters based on footprint
    width = 0.7
    total_length = 18.24
    
    # Cross-section for waveguides
    xs = gf.cross_section.cross_section(width=width, layer=(1, 0))
    
    # Calculate dimensions for U-shapes
    bend_radius = 0.35
    straight_length = (total_length - 2 * bend_radius) / 2
    
    # Build top U-shape (facing down)
    path_top = gf.Path()
    path_top.append(gf.path.straight(length=straight_length))
    path_top.append(gf.path.arc(radius=bend_radius, angle=180))
    path_top.append(gf.path.straight(length=straight_length))
    path_top.append(gf.path.arc(radius=bend_radius, angle=180))
    path_top.append(gf.path.straight(length=straight_length))
    
    wg_top = gf.path.extrude(p=path_top, cross_section=xs)
    ref_top = c << wg_top
    
    # Build bottom U-shape (facing up)
    path_bottom = gf.Path()
    path_bottom.append(gf.path.straight(length=straight_length))
    path_bottom.append(gf.path.arc(radius=bend_radius, angle=-180))
    path_bottom.append(gf.path.straight(length=straight_length))
    path_bottom.append(gf.path.arc(radius=bend_radius, angle=-180))
    path_bottom.append(gf.path.straight(length=straight_length))
    
    wg_bottom = gf.path.extrude(p=path_bottom, cross_section=xs)
    ref_bottom = c << wg_bottom
    # Offset bottom shape to face the top shape
    vertical_offset = -width - 0.2
    ref_bottom.move((0, vertical_offset))
    
    # Add straight bridge/connector in the middle
    bridge_width = 0.15
    bridge_xs = gf.cross_section.cross_section(width=bridge_width, layer=(1, 0))
    
    bridge_path = gf.path.straight(length=total_length)
    wg_bridge = gf.path.extrude(p=bridge_path, cross_section=bridge_xs)
    ref_bridge = c << wg_bridge
    ref_bridge.move((0, -width/2 - 0.1))
    
    # Add gate structures (the vertical rectangular patterns along the center sections)
    gate_count = 60
    gate_width = 0.04
    gate_height = 0.08
    gate_spacing = straight_length / gate_count
    
    for i in range(gate_count):
        x_pos = straight_length/2 + i * gate_spacing
        
        # Create vertical gate structure
        gate = gf.components.rectangle(
            size=(gate_width, gate_height),
            layer=(1, 0),
            centered=True
        )
        ref_gate = c << gate
        
        # Position gate across the gap between strands
        gate_y = -width/2 + vertical_offset/2
        ref_gate.move((x_pos, gate_y))
    
    # Add solid rectangles for the tip regions (no gates in the bent areas)
    tip_rect_xs = rectangle_xs = gf.cross_section.cross_section(width=width, layer=(1, 0))

    return c

if __name__ == "__main__":
    device().write_gds("device.gds")