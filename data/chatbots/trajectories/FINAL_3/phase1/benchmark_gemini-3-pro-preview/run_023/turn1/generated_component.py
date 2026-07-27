import gdsfactory as gf

@gf.cell
def coupler_parametric(length=240, height=4, gap=0.2, width=0.5, coupling_length=40):
    """
    Generates a directional coupler based on footprint constraints using
    catalog primitives (straight and bend_s).
    
    Args:
        length: Total device length (um). (Constraint: 240)
        height: Total device footprint height (um). (Constraint: 4)
        gap: Gap between waveguides in the coupling region.
        width: Waveguide width.
        coupling_length: Length of the central straight coupling region.
    """
    c = gf.Component()

    # 1. Define Cross Section
    # Standard silicon photonics layer typically (1,0)
    xs = gf.cross_section.cross_section(width=width, layer=(1, 0))

    # 2. Calculate Geometry Derived from Constraints
    
    # Calculate Y-positions for the coupling region (center-to-center)
    # The gap is the clear distance, so centers are offset by (gap/2 + width/2)
    y_coupling_offset = (gap / 2) + (width / 2)
    
    # Calculate Y-positions for the ports (center-to-center)
    # To fit exactly inside 'height', the top edge is at y=+height/2.
    # Therefore, the top waveguide center is at (height/2 - width/2).
    y_port_offset = (height / 2) - (width / 2)
    
    # Calculate parameters for the S-Bends
    # dy: Vertical shift required from coupling region to port
    dy = y_port_offset - y_coupling_offset
    
    # dx: Horizontal length available for one S-bend
    # Total length = bend + coupling + bend
    dx = (length - coupling_length) / 2

    # 3. Create Primitives
    
    # --- Coupling Region (Middle) ---
    # Create two straight waveguides
    wg_straight = gf.components.straight(length=coupling_length, cross_section=xs)
    
    # Add references and position them vertically
    coupling_top = c << wg_straight
    coupling_bot = c << wg_straight
    
    coupling_top.movey(y_coupling_offset)
    coupling_bot.movey(-y_coupling_offset)

    # --- Output Transitions (Right Side) ---
    # Top Output: S-bend going UP (positive dy) from straight to port
    bend_out_top = c << gf.components.bend_s(size=(dx, dy), cross_section=xs)
    bend_out_top.connect("o1", coupling_top.ports["o2"])
    
    # Bottom Output: S-bend going DOWN (negative dy) from straight to port
    bend_out_bot = c << gf.components.bend_s(size=(dx, -dy), cross_section=xs)
    bend_out_bot.connect("o1", coupling_bot.ports["o2"])

    # --- Input Transitions (Left Side) ---
    # Top Input: S-bend coming from port DOWN to straight (negative dy if viewing L->R)
    # We connect the END ("o2") of the bend to the START ("o1") of the straight.
    bend_in_top = c << gf.components.bend_s(size=(dx, -dy), cross_section=xs)
    bend_in_top.connect("o2", coupling_top.ports["o1"])
    
    # Bottom Input: S-bend coming from port UP to straight (positive dy if viewing L->R)
    bend_in_bot = c << gf.components.bend_s(size=(dx, dy), cross_section=xs)
    bend_in_bot.connect("o2", coupling_bot.ports["o1"])

    # 4. Expose Ports
    c.add_port("o1", port=bend_in_top.ports["o1"]) # Top Input
    c.add_port("o2", port=bend_in_bot.ports["o1"]) # Bottom Input
    c.add_port("o3", port=bend_out_top.ports["o2"]) # Top Output
    c.add_port("o4", port=bend_out_bot.ports["o2"]) # Bottom Output

    return c

if __name__ == "__main__":
    # Create the device matching the specific constraints
    device = coupler_parametric(length=240, height=4)
    
    # Save to GDS
    device.write_gds("coupler_4x240.gds")
    
    # Visualization (optional)
    device.show()