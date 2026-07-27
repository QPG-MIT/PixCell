import gdsfactory as gf

@gf.cell
def directional_coupler_4x240():
    """
    Recreation of the directional coupler based on image analysis
    and constrained to 4um x 240um footprint.
    """
    c = gf.Component()
    
    # 1. Define Cross Section
    # Standard silicon photonics width (0.5um)
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))

    # 2. Dimensions
    # Constraints
    L_total = 240.0
    H_total = 4.0
    
    # Internal Geometry
    L_coupler = 100.0  # Length of the straight interaction region
    L_bend = (L_total - L_coupler) / 2  # 70.0 um for each s-bend
    
    wg_width = 0.5
    gap = 0.2
    
    # Y-positions relative to center line (y=0)
    # Inner: Center of waveguides in the coupling region
    # y = +/- (gap/2 + width/2) = +/- 0.35
    y_inner_center = (gap + wg_width) / 2
    
    # Outer: Center of waveguides at the ports
    # y = +/- (H_total/2 - width/2) = +/- 1.75
    y_outer_center = (H_total / 2) - (wg_width / 2)
    
    # Vertical shift required for the S-bend
    dy = y_outer_center - y_inner_center # 1.75 - 0.35 = 1.4 um

    # 3. Create Primitives
    
    # Central interaction region
    # coupler_straight creates two parallel waveguides.
    # Standard ports: o1 (West Top), o2 (West Bottom), o3 (East Bottom), o4 (East Top)
    coupler = c << gf.components.coupler_straight(
        length=L_coupler, 
        gap=gap, 
        cross_section=xs
    )

    # S-Bends
    # We define bends with positive x-span.
    # bend_out_up: Shifts y by +dy (Goes "Up")
    # bend_out_down: Shifts y by -dy (Goes "Down")
    bend_out_up = gf.components.bend_s(size=(L_bend, dy), cross_section=xs)
    bend_out_down = gf.components.bend_s(size=(L_bend, -dy), cross_section=xs)

    # 4. Assemble and Connect
    
    # -- Left Side (Inputs) --
    # Connecting to West-facing ports (angle=180).
    # The 'connect' function aligns the ports, which effectively rotates the bend 180 degrees.
    # An (L, -dy) bend rotated 180 becomes (-L, +dy) -> Moves Left and Up.
    
    # Top Left Port: Connect to coupler o1 (West Top). Needs to flare Up-Left.
    # We use bend_out_down (dy negative). Rotated -> dy positive (Up).
    tl = c << bend_out_down
    tl.connect("o1", coupler.ports["o1"])

    # Bottom Left Port: Connect to coupler o2 (West Bottom). Needs to flare Down-Left.
    # We use bend_out_up (dy positive). Rotated -> dy negative (Down).
    bl = c << bend_out_up
    bl.connect("o1", coupler.ports["o2"])

    # -- Right Side (Outputs) --
    # Connecting to East-facing ports (angle=0).
    # No rotation occurs.
    
    # Top Right Port: Connect to coupler o4 (East Top). Needs to flare Up-Right.
    tr = c << bend_out_up
    tr.connect("o1", coupler.ports["o4"])

    # Bottom Right Port: Connect to coupler o3 (East Bottom). Needs to flare Down-Right.
    br = c << bend_out_down
    br.connect("o1", coupler.ports["o3"])

    # 5. Expose External Ports
    # We expose the 'o2' ports of the s-bends as the device ports
    c.add_port("o1", port=tl.ports["o2"]) # Input Top
    c.add_port("o2", port=bl.ports["o2"]) # Input Bottom
    c.add_port("o3", port=tr.ports["o2"]) # Output Top
    c.add_port("o4", port=br.ports["o2"]) # Output Bottom

    return c

if __name__ == "__main__":
    device = directional_coupler_4x240()
    device.write_gds("directional_coupler.gds")
    
    # Print design dimensions derived from parameters
    width = 240.0
    height = 4.0
    print(f"Device Footprint: {width:.2f} um x {height:.2f} um")