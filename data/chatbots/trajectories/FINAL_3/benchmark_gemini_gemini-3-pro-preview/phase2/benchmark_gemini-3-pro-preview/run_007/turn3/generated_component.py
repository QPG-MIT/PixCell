import gdsfactory as gf

@gf.cell
def directional_coupler():
    c = gf.Component()

    # 1. Define Design Parameters
    # Constraints: Footprint 120um x 4um
    total_length = 120.0
    total_height = 4.0
    
    # Waveguide specs
    # Gap 0.2um matches the tight coupling in the target image
    wg_width = 0.5
    gap = 0.2
    layer = (1, 0)
    
    xs = gf.cross_section.cross_section(width=wg_width, layer=layer)

    # 2. Geometry Calculation
    # Partition the length: 50% coupling, 25% for bends on each side
    length_straight = 60.0
    length_bend = (total_length - length_straight) / 2 # 30.0um
    
    # Create the Central Straight Coupler
    # This creates two parallel waveguides.
    coupler_core = c << gf.components.coupler_straight(
        length=length_straight, 
        gap=gap, 
        cross_section=xs
    )

    # 3. Calculate Vertical Shift (dy)
    # We want the outer ports to be at the edge of the 4um height constraint.
    # Center Y of the outer waveguide = (Total Height - Waveguide Width) / 2
    y_target_outer = (total_height - wg_width) / 2
    
    # Center Y of the inner waveguide (from coupler definition)
    y_inner = (gap + wg_width) / 2
    
    # The vertical distance the S-bend must cover
    dy = y_target_outer - y_inner

    # 4. Create and Connect S-Bends
    # We use specific port names ("o1" through "o4") to avoid the 'values()' error.
    # Mapping based on previous crossing error:
    # o1: Bottom-West, o2: Top-West, o3: Top-East, o4: Bottom-East
    
    # -- Left Side (Inputs) --
    
    # Top Left Input: Starts high, goes DOWN to coupler
    # Size Y is negative (-dy) to drop
    bend_tl = c << gf.components.bend_s(size=(length_bend, -dy), cross_section=xs)
    # Connect END ("o2") of bend to Top-West ("o2") of coupler
    bend_tl.connect("o2", coupler_core.ports["o2"])
    
    # Bottom Left Input: Starts low, goes UP to coupler
    # Size Y is positive (dy) to rise
    bend_bl = c << gf.components.bend_s(size=(length_bend, dy), cross_section=xs)
    # Connect END ("o2") of bend to Bottom-West ("o1") of coupler
    bend_bl.connect("o2", coupler_core.ports["o1"])
    
    # -- Right Side (Outputs) --
    
    # Top Right Output: Starts at coupler, goes UP to edge
    # Size Y is positive (dy) to rise
    bend_tr = c << gf.components.bend_s(size=(length_bend, dy), cross_section=xs)
    # Connect START ("o1") of bend to Top-East ("o3") of coupler
    bend_tr.connect("o1", coupler_core.ports["o3"])
    
    # Bottom Right Output: Starts at coupler, goes DOWN to edge
    # Size Y is negative (-dy) to drop
    bend_br = c << gf.components.bend_s(size=(length_bend, -dy), cross_section=xs)
    # Connect START ("o1") of bend to Bottom-East ("o4") of coupler
    bend_br.connect("o1", coupler_core.ports["o4"])

    # 5. Add Ports to Top Level
    c.add_port("o1", port=bend_tl.ports["o1"]) # Top Input
    c.add_port("o2", port=bend_bl.ports["o1"]) # Bottom Input
    c.add_port("o3", port=bend_tr.ports["o2"]) # Top Output
    c.add_port("o4", port=bend_br.ports["o2"]) # Bottom Output

    return c

if __name__ == "__main__":
    device = directional_coupler()
    device.write_gds("directional_coupler.gds")