import gdsfactory as gf

@gf.cell
def tapered_curved_device():
    """
    Constructs the device by combining a straight center taper with 
    curved outer arms using path extrusion.
    """
    c = gf.Component()

    # 1. Define the width transition (from thin to thick)
    # Using a slightly larger start/end width for the arms to match the target
    xs_thin = gf.cross_section.cross_section(width=0.2, layer=(1, 0))
    xs_thick = gf.cross_section.cross_section(width=0.6, layer=(1, 0))
    transition = gf.path.transition(xs_thin, xs_thick)

    # 2. Central Waveguide (Simple Taper)
    # The center element is a simple, straight taper
    center_taper = c << gf.components.taper(length=40, width1=0.1, width2=0.5)

    # 3. Outer Waveguides (Curved paths)
    # Create a path: Straight -> Euler Bend (outward) -> Straight
    p = gf.Path()
    p.append(gf.path.straight(length=15))
    p.append(gf.path.euler(radius=25, angle=20))
    p.append(gf.path.straight(length=10))

    # Extrude the path with the width transition to create the 'flare'
    arm_wg = gf.path.extrude_transition(p, transition)

    # 4. Position the arms
    # Instead of boolean unions, we add references directly to the component.
    # This avoids the rendering artifacts seen in the previous iteration.
    
    # Top Arm
    top_ref = c << arm_wg
    top_ref.movey(1.3) # Offset to create the visual gap

    # Bottom Arm (Mirror the top)
    bot_ref = c << arm_wg
    bot_ref.mirror(p1=(0, 0), p2=(1, 0))
    bot_ref.movey(-1.3)

    return c

# Create and save
device = tapered_curved_device()
device.write_gds("curved_tapered_device.gds")

if __name__ == "__main__":
    device.show()