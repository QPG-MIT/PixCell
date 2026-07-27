import gdsfactory as gf

@gf.cell
def device_generator():
    """
    Recreates the racetrack resonator with internal heater structures.
    Fixes the min_bend_radius error by setting radius=None in the trace cross-section.
    """
    c = gf.Component("Racetrack_Device_Corrected")
    
    # --- Configuration ---
    # Dimensions derived from 5.5µm x 3.0µm footprint
    footprint_w = 5.5
    footprint_h = 3.0
    layer = (1, 0)
    
    # Outer Ring Geometry
    ring_width = 0.5
    outer_radius = footprint_h / 2.0  # 1.5
    center_radius = outer_radius - (ring_width / 2.0) # 1.25
    straight_length = footprint_w - (2 * outer_radius) # 2.5
    
    # Inner Arm Parameters
    pad_width = 0.7
    pad_height = 0.4
    gap = 0.15
    taper_length = 0.3
    trace_width = 0.15
    bend_dx = 0.6
    bend_dy = 0.3
    arm_y_offset = 0.65
    
    # Define Cross Sections
    # CRITICAL FIX: Set radius=None for xs_trace to allow tight S-bends
    xs_ring = gf.cross_section.cross_section(width=ring_width, layer=layer)
    xs_pad = gf.cross_section.cross_section(width=pad_height, layer=layer)
    xs_trace = gf.cross_section.cross_section(width=trace_width, layer=layer, radius=None)

    # ---------------------------
    # 1. Construct Outer Ring
    # ---------------------------
    p = gf.Path()
    p.append(gf.path.straight(length=straight_length))
    p.append(gf.path.arc(radius=center_radius, angle=180))
    p.append(gf.path.straight(length=straight_length))
    p.append(gf.path.arc(radius=center_radius, angle=180))
    
    ring = c << gf.path.extrude(p, cross_section=xs_ring)
    
    # Center the ring. Path logic: 
    # (0,0)->(L,0)->Arc->(0, 2R)->Straight->(0, 2R)->Arc->(0,0).
    # Geometric center is at (L/2, R).
    ring.move((-straight_length / 2, -center_radius))

    # ---------------------------
    # 2. Construct Inner Arm
    # ---------------------------
    arm = gf.Component("Inner_Arm")
    
    # Left Pad
    pad_l = arm << gf.components.straight(length=pad_width, cross_section=xs_pad)
    pad_l.move((-pad_width - gap/2, 0))
    
    # Right Pad
    pad_r = arm << gf.components.straight(length=pad_width, cross_section=xs_pad)
    pad_r.move((gap/2, 0))
    
    # Left Taper (Trace -> Pad)
    taper_l = arm << gf.components.taper(length=taper_length, width1=trace_width, width2=pad_height, layer=layer)
    taper_l.connect("o2", pad_l.ports["o1"])
    
    # Right Taper (Pad -> Trace)
    taper_r = arm << gf.components.taper(length=taper_length, width1=pad_height, width2=trace_width, layer=layer)
    taper_r.connect("o1", pad_r.ports["o2"])
    
    # Left S-Bend
    # Connects to the thin end of the taper.
    # Bends "out" (away from center Y=0 of the arm) to simulate the look in the image.
    bend_l = arm << gf.components.bend_s(size=(bend_dx, -bend_dy), cross_section=xs_trace)
    bend_l.connect("o2", taper_l.ports["o1"]) 
    
    # Right S-Bend
    bend_r = arm << gf.components.bend_s(size=(bend_dx, -bend_dy), cross_section=xs_trace)
    bend_r.connect("o1", taper_r.ports["o2"])
    
    # ---------------------------
    # 3. Assemble Device
    # ---------------------------
    # Top Arm
    top_ref = c << arm
    top_ref.movey(arm_y_offset)
    
    # Bottom Arm (Mirrored)
    bot_ref = c << arm
    bot_ref.mirror_y() 
    bot_ref.movey(-arm_y_offset)

    return c

if __name__ == "__main__":
    device = device_generator()
    device.write_gds("racetrack_heater_corrected.gds")
    device.show()