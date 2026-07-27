import gdsfactory as gf

@gf.cell
def tapered_curved_device():
    """
    Constructs the device by combining a straight center taper with 
    curved outer arms using path extrusion.
    """
    c = gf.Component()

    # 1. Define the width transition (from thin to thick)
    # This creates the "flaring" effect seen in the outer waveguides
    xs_thin = gf.cross_section.cross_section(width=0.1, layer=(1, 0))
    xs_thick = gf.cross_section.cross_section(width=0.8, layer=(1, 0))
    transition = gf.path.transition(xs_thin, xs_thick)

    # 2. Central Waveguide (Straight taper)
    # We use a simple taper for the center section
    center_taper = c << gf.components.taper(length=40, width1=0.2, width2=0.4)

    # 3. Outer Waveguides (Curved paths)
    # Define a path that goes straight, curves out, then continues
    p = gf.Path()
    p.append(gf.path.straight(length=10))
    p.append(gf.path.euler(radius=30, angle=20)) # Adds the curvature
    p.append(gf.path.straight(length=15))

    # Extrude the path with the width transition
    top_arm_wg = gf.path.extrude_transition(p, transition)
    bot_arm_wg = gf.path.extrude_transition(p, transition)

    # 4. Position the arms
    top_ref = c << top_arm_wg
    top_ref.movey(1.2) # Offset to match visual spacing

    bot_ref = c << bot_arm_wg
    bot_ref.mirror(p1=(0, 0), p2=(1, 0)) # Mirror for the bottom arm
    bot_ref.movey(-1.2)

    # 5. Boolean Union
    # Combine everything into one single piece of geometry
    # We union the center with the top, then with the bottom
    mid_union = gf.boolean(top_ref, center_taper, operation="or", layer=(1, 0))
    final_device = gf.boolean(mid_union, bot_ref, operation="or", layer=(1, 0))

    return final_device

# Create and save
device = tapered_curved_device()
device.write_gds("curved_tapered_device.gds")

if __name__ == "__main__":
    device.show()