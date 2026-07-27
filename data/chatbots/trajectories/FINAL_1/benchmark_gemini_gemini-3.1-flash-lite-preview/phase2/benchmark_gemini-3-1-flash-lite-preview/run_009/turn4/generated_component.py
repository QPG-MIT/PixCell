import gdsfactory as gf

@gf.cell
def tapered_curved_device():
    """
    Constructs a 3-part tapered device with tight gaps and shallow curvature.
    """
    c = gf.Component()

    # 1. Geometry parameters for tight layout
    length = 40.0
    w_start = 0.1
    w_end = 0.5
    gap = 0.15 # Small gap to match the tight density of the target
    
    # Calculate vertical offset so waveguides don't overlap but are close
    # Width ~0.5 at end. Center + Gap + Half of top/bottom arm
    # (0.5 / 2) + gap + (0.5 / 2) = 0.65
    y_offset = (w_end / 2) + gap + (w_end / 2) 

    # 2. Define the width transition
    # We use a simple cross-section transition
    xs_start = gf.cross_section.cross_section(width=w_start, layer=(1, 0))
    xs_end = gf.cross_section.cross_section(width=w_end, layer=(1, 0))
    transition = gf.path.transition(xs_start, xs_end, width_type="linear")

    # 3. Central Waveguide (Taper)
    center_taper = c << gf.components.taper(length=length, width1=w_start, width2=w_end)

    # 4. Outer Waveguides (Shallow curve paths)
    # Start with a path that is straight, then curves gently outward
    p = gf.Path()
    p.append(gf.path.straight(length=20))
    # Using a large radius and small angle creates the subtle 'flare' seen in the target
    p.append(gf.path.euler(radius=100, angle=15, p=0.5)) 
    
    # Extrude the path with the width transition
    arm_wg = gf.path.extrude_transition(p, transition)

    # 5. Position the arms precisely
    # Top Arm
    top_ref = c << arm_wg
    top_ref.movey(y_offset)

    # Bottom Arm (Mirror the top)
    bot_ref = c << arm_wg
    bot_ref.mirror(p1=(0, 0), p2=(1, 0))
    bot_ref.movey(-y_offset)

    return c

# Create and save
device = tapered_curved_device()
device.write_gds("curved_tapered_device.gds")

if __name__ == "__main__":
    device.show()