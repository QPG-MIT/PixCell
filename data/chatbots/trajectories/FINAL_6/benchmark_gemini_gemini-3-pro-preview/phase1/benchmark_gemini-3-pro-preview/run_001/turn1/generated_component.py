import gdsfactory as gf
import numpy as np

@gf.cell
def device_design():
    c = gf.Component()

    # 1. Define Dimensions based on 4.7um footprint
    # Total radius = 2.35um
    # We split the radius into: Taper Up (0.9) + Taper Down (0.9) + Tip (0.55) = 2.35
    l_taper_half = 0.9
    l_tip = 0.55
    
    # Widths estimated from image proportions
    w_thin = 0.25  # Width at center connection and at the tip
    w_fat = 1.1    # Maximum width of the petal

    # 2. Define Cross Sections
    xs_thin = gf.cross_section.cross_section(width=w_thin, layer=(1, 0))
    xs_fat = gf.cross_section.cross_section(width=w_fat, layer=(1, 0))

    # 3. Create the "Arm" Sub-Component
    # The arm consists of: Sine Taper Up -> Sine Taper Down -> Straight Tip
    arm = gf.Component("arm")

    # Segment 1: Taper from center (thin) to middle (fat) using sine profile for smooth curve
    path_up = gf.path.straight(length=l_taper_half)
    trans_up = gf.path.transition(xs_thin, xs_fat, width_type='sine')
    seg1 = arm << gf.path.extrude_transition(path_up, trans_up)

    # Segment 2: Taper from middle (fat) to tip start (thin)
    path_down = gf.path.straight(length=l_taper_half)
    trans_down = gf.path.transition(xs_fat, xs_thin, width_type='sine')
    seg2 = arm << gf.path.extrude_transition(path_down, trans_down)

    # Segment 3: Straight rectangular tip
    tip = arm << gf.components.straight(length=l_tip, cross_section=xs_thin)

    # Connect the segments
    # seg1 starts at (0,0) by default. Connect seg2 to end of seg1.
    seg2.connect("o1", seg1.ports["o2"])
    tip.connect("o1", seg2.ports["o2"])

    # Expose the starting port of the arm (at the center)
    arm.add_port("o1", port=seg1.ports["o1"])

    # 4. Assemble the final device by rotating the arm
    # Place 4 copies rotated by 90 degrees each
    for angle in [0, 90, 180, 270]:
        ref = c << arm
        ref.rotate(angle)
        # Since the arm was built starting at (0,0), rotating it keeps the center aligned.

    return c

# Generate and write the GDS file
if __name__ == "__main__":
    component = device_design()
    component.write_gds("design.gds")
    component.show()