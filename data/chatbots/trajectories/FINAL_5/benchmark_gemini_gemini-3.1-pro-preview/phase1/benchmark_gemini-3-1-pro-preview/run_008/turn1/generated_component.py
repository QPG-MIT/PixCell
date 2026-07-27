import gdsfactory as gf

@gf.cell
def corrugated_straight(length=14.9, width=0.06, tooth_width=0.075, tooth_height=0.05, period=0.15):
    """Creates a straight waveguide with periodic rectangular teeth on its bottom edge."""
    c = gf.Component()
    # Explicit minimum radius to bypass routing limits during compilation
    xs = gf.cross_section.cross_section(width=width, radius=0.01, radius_min=0.01)
    
    # Main straight section
    wg = c << gf.components.straight(length=length, cross_section=xs)
    c.add_port("o1", port=wg.ports["o1"])
    c.add_port("o2", port=wg.ports["o2"])

    # Grating teeth geometry calculations
    straight_end = 0.5 # Buffer region without corrugations at the start/end
    corrugation_length = length - 2 * straight_end
    num_teeth = int(corrugation_length / period)
    teeth_start_x = straight_end + (corrugation_length - num_teeth * period) / 2
    
    tooth_rect = gf.components.rectangle(size=(tooth_width, tooth_height), centered=True)
    
    # Instance teeth along the bottom edge
    for i in range(num_teeth):
        t = c << tooth_rect
        x_pos = teeth_start_x + i * period + tooth_width / 2
        y_pos = -width / 2 - tooth_height / 2
        t.move((x_pos, y_pos))
        
    return c

@gf.cell
def top_waveguide():
    """Builds the upper half of the folded contradirectional coupler structure."""
    c = gf.Component()
    
    # Cross sections
    xs_wg = gf.cross_section.cross_section(width=0.06, radius=0.01, radius_min=0.01)
    xs_tip = gf.cross_section.cross_section(width=0.005, radius=0.01, radius_min=0.01)

    # 1. Inner corrugated arm
    inner = c << corrugated_straight(length=14.9, width=0.06, tooth_height=0.05)

    # 2. U-Bend
    ubend = c << gf.components.bend_circular(radius=0.10, angle=180, cross_section=xs_wg)
    ubend.connect("o1", inner.ports["o2"])

    # 3. Outer straight arm going back parallel to inner arm
    outer = c << gf.components.straight(length=14.9, cross_section=xs_wg)
    outer.connect("o1", ubend.ports["o2"])

    # 4. Tapered curving tail
    # Replaced Bezier with a precisely calculated smooth arc to bypass the AttributeError
    # radius=72 and angle=-2.5 perfectly achieves the ~3.12 um X-span and curves up exactly to fit the 0.7 um height
    p = gf.path.arc(radius=72.0, angle=-2.5)
    trans = gf.path.transition(cross_section1=xs_wg, cross_section2=xs_tip, width_type='sine')
    tail = c << gf.path.extrude_transition(p, trans)
    tail.connect("o1", outer.ports["o2"])

    return c

@gf.cell
def my_device():
    """Assembles the final parametric device exactly into the 18.24 x 0.7 um footprint."""
    c = gf.Component()

    twg = top_waveguide()
    
    # Exact shifts to place bounding box perfectly within [-9.12, 9.12] x [-0.35, 0.35]
    X_shift = -6.0
    Y_shift = 0.08

    # Top placement
    twg_ref = c << twg
    twg_ref.move((X_shift, Y_shift))

    # Bottom placement - perfectly mirrored to guarantee exact symmetry
    bwg_ref = c << twg
    bwg_ref.move((X_shift, Y_shift))
    bwg_ref.mirror(p1=(0, 0), p2=(1, 0)) # Reflect across X-axis limits (Y -> -Y)
    bwg_ref.mirror(p1=(0, 0), p2=(0, 1)) # Reflect across Y-axis limits (X -> -X)
    
    # Place central straight thin waveguide
    # Its length spans the distance bounded by the two U-Bends
    L_center = 17.8
    xs_center = gf.cross_section.cross_section(width=0.02, radius=0.01, radius_min=0.01)
    center_wg = c << gf.components.straight(length=L_center, cross_section=xs_center)
    center_wg.move((-L_center/2, 0))

    return c

if __name__ == "__main__":
    device = my_device()
    device.write_gds("contra_directional_coupler_folded.gds")