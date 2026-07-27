import gdsfactory as gf

@gf.cell
def directional_coupler_corrected():
    c = gf.Component()

    # 1. Define Dimensions based on constraint 120um x 4um
    total_length = 120.0
    total_height = 4.0
    
    # Waveguide parameters
    wg_width = 0.5
    gap = 0.2
    
    # Length of the straight parallel coupling region
    # Adjusted to 50um to visually match the proportions of the original image
    coupling_length = 50.0 
    bend_length = (total_length - coupling_length) / 2

    # 2. Calculate Vertical Positions (Y-coordinates)
    # y_inner: Center Y of the waveguide in the coupling region (close to 0)
    # 0.2 gap means center is at +/- (0.1 + 0.25) = +/- 0.35
    y_inner = (gap / 2) + (wg_width / 2)
    
    # y_outer: Center Y of the waveguide at the input/output ports
    # 4.0 height means limits are +/- 2.0. Center of WG is at 2.0 - 0.25 = 1.75
    y_outer = (total_height / 2) - (wg_width / 2)
    
    # The vertical distance the S-bend needs to cover
    dy = y_outer - y_inner

    # 3. Define Primitives
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))
    
    # Straight section for coupling
    straight = gf.components.straight(length=coupling_length, cross_section=xs)
    
    # We need two types of bends:
    # bend_up: goes from y=0 to y=+dy (Left to Right)
    # bend_down: goes from y=0 to y=-dy (Left to Right)
    bend_up = gf.components.bend_s(size=(bend_length, dy), cross_section=xs)
    bend_down = gf.components.bend_s(size=(bend_length, -dy), cross_section=xs)

    # 4. Assemble Top Arm
    # Place coupling region
    top_str = c << straight
    top_str.movey(y_inner)
    
    # Top Input: Needs to start high and go DOWN to the straight section.
    # We use 'bend_down' connecting its end (o2) to the straight start (o1).
    # Wait: bend_down goes (0,0)->(L, -dy). 
    # If we connect o2 (L, -dy) to straight (0, y_inner), 
    # then o1 is at (-L, y_inner + dy) = (-L, y_outer). This is correct!
    top_in = c << bend_down
    top_in.connect("o2", top_str.ports["o1"])
    
    # Top Output: Needs to go UP from straight to outer.
    top_out = c << bend_up
    top_out.connect("o1", top_str.ports["o2"])

    # 5. Assemble Bottom Arm
    # Place coupling region
    bot_str = c << straight
    bot_str.movey(-y_inner)
    
    # Bottom Input: Needs to start low and go UP to the straight section.
    # We use 'bend_up' connecting its end (o2) to the straight start (o1).
    # bend_up goes (0,0)->(L, dy).
    # Connecting o2 (L, dy) to straight (0, -y_inner).
    # o1 is at (-L, -y_inner - dy) = (-L, -y_outer). This is correct!
    bot_in = c << bend_up
    bot_in.connect("o2", bot_str.ports["o1"])
    
    # Bottom Output: Needs to go DOWN from straight to outer.
    bot_out = c << bend_down
    bot_out.connect("o1", bot_str.ports["o2"])

    # 6. Expose Ports
    c.add_port("o1", port=top_in.ports["o1"])
    c.add_port("o2", port=bot_in.ports["o1"])
    c.add_port("o3", port=top_out.ports["o2"])
    c.add_port("o4", port=bot_out.ports["o2"])

    return c

if __name__ == "__main__":
    device = directional_coupler_corrected()
    device.write_gds("directional_coupler_corrected.gds")
    device.show()
    print(f"Device width: {device.dx}")
    print(f"Device height: {device.dy}")