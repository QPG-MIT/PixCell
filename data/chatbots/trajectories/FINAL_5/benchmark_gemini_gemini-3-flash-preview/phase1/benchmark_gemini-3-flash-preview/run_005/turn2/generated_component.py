import gdsfactory as gf
import numpy as np

def create_bezier_points(p0, p1, p2, p3, n=60):
    """Generates cubic bezier points for the 'swooping' tail."""
    t = np.linspace(0, 1, n)
    # Standard cubic Bezier formula
    pts = (1-t)[:, None]**3 * p0 + 3*(1-t)[:, None]**2 * t[:, None] * p1 + \
          3*(1-t)[:, None] * t[:, None]**2 * p2 + t[:, None]**3 * p3
    return [tuple(np.round(p, 4)) for p in pts]

@gf.cell
def fishbone_half(
    width: float = 0.04,        # 40nm is even, satisfying the DBU parity requirement
    radius_bend: float = 0.10,
    total_len: float = 18.24,
    comb_len: float = 12.0,
    tooth_height: float = 0.16,
    layer: tuple[int, int] = (1, 0),
) -> gf.Component:
    """
    Constructs one half of the device with a needle arm, 
    small-radius bend, and a striated fishbone backbone.
    """
    c = gf.Component()
    
    # Initialize cross section with grid-safe width and zeroed radius constraint
    xs = gf.cross_section.cross_section(width=width, layer=layer, radius_min=0.01)

    # 1. Outer Needle Arm (Left-to-Right)
    # Sharp taper at the start to create the needle point
    taper_len = 3.60
    straight_len = total_len - taper_len - (radius_bend * 2)
    
    arm_s = c << gf.components.straight(length=straight_len, cross_section=xs)
    arm_t = c << gf.components.taper(
        length=taper_len, width1=0.002, width2=width, cross_section=xs
    )
    arm_t.connect("o2", arm_s.ports["o1"])

    # 2. 180-Degree Euler Bend (U-Turn)
    bend = c << gf.components.bend_euler(radius=radius_bend, angle=180, cross_section=xs)
    bend.connect("o1", arm_s.ports["o2"])

    # 3. Inner Backbone & Striated "Comb"
    # Backbone connects the bend to the tail
    backbone = c << gf.components.straight(length=comb_len, cross_section=xs)
    backbone.connect("o1", bend.ports["o2"])

    # Create the striated texture using Boolean subtraction
    # This creates the appearance of fine vertical lines seen in the image
    comb_rect = gf.components.rectangle(size=(comb_len, tooth_height), layer=layer, centered=True)
    num_teeth = 90
    slot_w = 0.02  # 20nm gaps
    slots_comp = gf.Component()
    pitch = comb_len / (num_teeth + 1)
    for i in range(num_teeth):
        s = slots_comp << gf.components.rectangle(size=(slot_w, tooth_height * 0.9), layer=layer, centered=True)
        s.movex(-comb_len/2 + (i + 1) * pitch)
    
    comb_body = gf.boolean(A=comb_rect, B=slots_comp, operation="not", layer=layer)
    comb_ref = c << comb_body
    # Align the textured block below the inner backbone
    comb_ref.move((backbone.center[0], backbone.center[1] - tooth_height/2 - width/2))

    # 4. Swooping Curved Tail
    # Manual bezier points create the organic flare at the left end
    p0 = np.array([0, 0])
    p1 = np.array([-1.0, 0])
    p2 = np.array([-2.4, 0.22])
    p3 = np.array([-3.4, 0.50])
    pts = create_bezier_points(p0, p1, p2, p3)
    
    tail_path = gf.Path(pts)
    tail = c << gf.path.extrude(tail_path, cross_section=xs)
    tail.connect("o1", backbone.ports["o2"])

    return c

@gf.cell
def device_geometry() -> gf.Component:
    """
    Assembles the final point-symmetric device within 18.24um x 0.70um.
    """
    c = gf.Component()
    
    half = fishbone_half()

    # Top unit placement
    top = c << half
    top.movey(0.12)

    # Bottom unit placement (mirrored and rotated)
    bottom = c << half
    bottom.rotate(180)
    bottom.movey(-0.12)

    # Central Divider Bar (solid thin line)
    c << gf.components.rectangle(size=(18.24, 0.02), layer=(1, 0), centered=True)

    # Center entire geometry at (0,0)
    c.move((-c.center[0], -c.center[1]))
    return c

if __name__ == "__main__":
    device = device_geometry()
    device.write_gds("fishbone_final_fixed.gds")
    
    # Final Size Check
    print(f"Final Geometry Size: {device.xsize:.3f} um x {device.ysize:.3f} um")
    print("Target Constraints: 18.24 um x 0.70 um")