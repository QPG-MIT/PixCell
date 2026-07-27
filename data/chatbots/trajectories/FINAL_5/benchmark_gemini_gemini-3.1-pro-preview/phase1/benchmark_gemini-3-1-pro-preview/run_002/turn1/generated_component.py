import gdsfactory as gf

@gf.cell
def grating_coupler_half():
    """
    Constructs one half (top) of the point-symmetric contra-directional coupler.
    """
    c = gf.Component()
    
    # Define widths as even multiples of DBU (1 nm) to avoid snapping errors
    w = 0.08      # Main waveguide width (80 nm)
    w_tip = 0.006 # Taper tip width (6 nm)
    
    # Define cross sections with `radius_min` disabled/lowered to allow tight U-turns
    xs = gf.cross_section.cross_section(width=w, radius_min=0.01)
    xs_tip = gf.cross_section.cross_section(width=w_tip, radius_min=0.01)

    # ---------------------------------------------------------
    # 1. Inner Waveguide (Straight + Taper)
    # ---------------------------------------------------------
    # Straight Taper
    taper_in = c << gf.components.taper(length=2.5, width1=w_tip, width2=w, cross_section=xs)
    taper_in.move((-8.5, 0.12)) # Starts at x=-8.5, ends at x=-6.0

    # Main Inner Straight
    str_in = c << gf.components.straight(length=14.42, cross_section=xs)
    str_in.move((-6.0, 0.12))

    # ---------------------------------------------------------
    # 2. Outer Waveguide (Curved Taper + Straight)
    # ---------------------------------------------------------
    # Curved Taper using a Bezier path to smoothly curve upwards and outwards
    p_out = gf.path.bezier(control_points=[(-8.5, 0.34), (-7.5, 0.28), (-6.0, 0.28)])
    trans = gf.path.transition(xs_tip, xs, width_type='sine')
    c << gf.path.extrude_transition(p_out, trans)

    # Main Outer Straight
    str_out = c << gf.components.straight(length=14.42, cross_section=xs)
    str_out.move((-6.0, 0.28))

    # ---------------------------------------------------------
    # 3. U-Turn Connecting Outer and Inner
    # ---------------------------------------------------------
    # Radius is exactly half the distance between outer (0.28) and inner (0.12)
    uturn = c << gf.components.bend_circular(radius=0.08, angle=-180, cross_section=xs)
    uturn.move((8.42, 0.28)) # Aligns with the end of the straight segments

    # ---------------------------------------------------------
    # 4. Gratings (Corrugated Teeth)
    # ---------------------------------------------------------
    # Create a single tooth
    tooth = gf.components.rectangle(size=(0.04, 0.03), centered=True)
    
    # Array the teeth along the inner straight waveguide
    # Y=0.065 places the top edge of the 0.03-high tooth exactly at Y=0.08 (the waveguide boundary)
    teeth = c.add_array(tooth, columns=90, rows=1, spacing=(0.15, 0))
    teeth.move((-5.5, 0.065)) 

    return c

@gf.cell
def contra_directional_coupler():
    """
    Assembles the full device with a central straight and two symmetric coupling structures.
    """
    c = gf.Component("contra_dc")
    w = 0.08
    xs = gf.cross_section.cross_section(width=w, radius_min=0.01)

    # 1. Central Straight Waveguide (Exact footprint length: 18.24 µm)
    center_wg = c << gf.components.straight(length=18.24, cross_section=xs)
    center_wg.move((-9.12, 0.0))

    # 2. Top Coupling Structure
    c << grating_coupler_half()

    # 3. Bottom Coupling Structure (180-degree point symmetry)
    bottom = c << grating_coupler_half()
    bottom.rotate(180)

    return c

if __name__ == "__main__":
    device = contra_directional_coupler()
    device.show()