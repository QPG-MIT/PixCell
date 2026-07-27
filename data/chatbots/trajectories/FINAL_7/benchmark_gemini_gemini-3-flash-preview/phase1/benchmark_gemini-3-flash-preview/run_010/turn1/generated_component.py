import gdsfactory as gf

@gf.cell
def make_double_box(layer=(1, 0)):
    """Creates the internal arm structure with two hollow boxes."""
    db = gf.Component()
    
    # Define primitives for the arm sub-structure
    # Height of structure is 0.4um, length is 1.8um
    h_rail = gf.components.rectangle(size=(1.8, 0.1), layer=layer, centered=True)
    v_end = gf.components.rectangle(size=(0.1, 0.4), layer=layer, centered=True)
    v_mid = gf.components.rectangle(size=(0.2, 0.4), layer=layer, centered=True)
    
    # Assembly using references
    r1 = db << h_rail
    r1.movey(0.15)
    
    r2 = db << h_rail
    r2.movey(-0.15)
    
    v1 = db << v_end
    v1.movex(-0.85) # (1.8/2 - 0.1/2)
    
    v2 = db << v_end
    v2.movex(0.85)
    
    db << v_mid # Centered middle divider
    
    return db

@gf.cell
def recreate_device():
    """
    Recreates the device geometry within a [3.0, 5.5] um footprint.
    Composition: Racetrack + Double-box arms + S-bend connectors.
    """
    c = gf.Component()
    layer = (1, 0)
    
    # --- Dimensions ---
    # Total Height 3.0 -> R=1.3, width=0.4
    # Total Width 5.5 -> L=2.5, R=1.3, width=0.4 (2.5 + 2*1.3 + 0.4 = 5.5)
    ring_width = 0.4
    R = 1.3
    L = 2.5
    
    # IMPORTANT: Set radius_min=None to bypass the default 10um radius check
    xs_ring = gf.cross_section.cross_section(width=ring_width, layer=layer, radius_min=None)
    xs_arm = gf.cross_section.cross_section(width=0.2, layer=layer, radius_min=None)
    
    # --- 1. Outer Racetrack ---
    p = gf.path.straight(length=L)
    p += gf.path.arc(radius=R, angle=180)
    p += gf.path.straight(length=L)
    p += gf.path.arc(radius=R, angle=180)
    
    ring_ref = c << gf.path.extrude(p, cross_section=xs_ring)
    ring_ref.move((-L/2, -R))
    
    # --- 2. Internal Arms ---
    db_comp = make_double_box(layer=layer)
    arm_y_offset = 0.65
    
    arm_top = c << db_comp
    arm_top.movey(arm_y_offset)
    
    arm_bot = c << db_comp
    arm_bot.movey(-arm_y_offset)
    
    # --- 3. S-bend Connectors ---
    # Connecting Box ends (x=0.9) to Ring inner wall (x=1.25)
    # size = (dx, dy) = (0.35, 0.65)
    sb_comp = gf.components.bend_s(size=(0.35, 0.65), cross_section=xs_arm)
    
    # Left side (pointing left from arm to ring center-left)
    tl = c << sb_comp
    tl.rotate(180)
    tl.move((-0.9, arm_y_offset))
    
    bl = c << sb_comp
    bl.mirror()
    bl.move((-0.9, -arm_y_offset))
    
    # Right side (pointing right from arm to ring center-right)
    tr = c << sb_comp
    tr.mirror()
    tr.rotate(180)
    tr.move((0.9, arm_y_offset))
    
    br = c << sb_comp
    br.move((0.9, -arm_y_offset))
    
    return c

if __name__ == "__main__":
    device = recreate_device()
    device.show()