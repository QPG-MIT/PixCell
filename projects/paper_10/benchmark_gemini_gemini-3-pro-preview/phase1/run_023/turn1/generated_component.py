import gdsfactory as gf
from gdsfactory.components import rectangle, taper, straight, bend_euler

@gf.cell
def device_racetrack_mzm_fixed():
    """
    Recreates the racetrack resonator device with corrected parameters.
    Fixed: Explicitly sets cross_section radius to avoid ValueError.
    """
    c = gf.Component()

    # --- 1. Dimensions based on footprint (3.0 x 5.5 um) ---
    # Height = 3.0um. 
    # Structure height = 2 * Radius + Width_bend. 
    # 3.0 = 2*R + 0.7  =>  2R = 2.3  =>  R = 1.15
    bend_radius = 1.15
    bend_width = 0.7
    
    # Width = 5.5um.
    # Structure width = 2 * (Bend_x) + Straight_length.
    # Bend_x (180 Euler) approx R + Width/2 = 1.5.
    # Straight_length = 5.5 - 2*(1.5) = 2.5
    total_straight_length = 2.5
    
    # Inner arm details
    arm_width = 0.35
    taper_len = 0.4
    straight_wg_len = total_straight_length - 2 * taper_len # 1.7
    
    # Pad details (visual estimate)
    pad_width = 0.8
    pad_height = 0.6
    pad_gap = 0.3

    # --- 2. Define Custom Cross Sections ---
    # FIX: We pass 'radius' and 'radius_min' to override default checks
    xs_bend = gf.cross_section.cross_section(
        width=bend_width, 
        layer=(1, 0),
        radius=bend_radius,
        radius_min=bend_radius  # Explicitly allow this small radius
    )
    
    xs_arm = gf.cross_section.cross_section(
        width=arm_width, 
        layer=(1, 0)
    )

    # --- 3. Build the Active Straight Arm ---
    # Helper to build the straight section with tapers and pads
    arm = gf.Component("active_arm")
    
    # Input Taper
    t1 = arm << taper(length=taper_len, width1=bend_width, width2=arm_width, layer=(1,0))
    
    # Straight waveguide
    wg = arm << straight(length=straight_wg_len, cross_section=xs_arm)
    wg.connect("o1", t1.ports["o2"])
    
    # Output Taper
    t2 = arm << taper(length=taper_len, width1=arm_width, width2=bend_width, layer=(1,0))
    t2.connect("o1", wg.ports["o2"])
    
    # Pads (centered on the straight section)
    center_x = taper_len + straight_wg_len / 2
    
    # Left Pad
    p1 = arm << rectangle(size=(pad_width, pad_height), layer=(1,0), centered=True)
    p1.move((center_x - pad_width/2 - pad_gap/2, 0))
    
    # Right Pad
    p2 = arm << rectangle(size=(pad_width, pad_height), layer=(1,0), centered=True)
    p2.move((center_x + pad_width/2 + pad_gap/2, 0))
    
    # Expose ports
    arm.add_port("o1", port=t1.ports["o1"])
    arm.add_port("o2", port=t2.ports["o2"])

    # --- 4. Assembly ---
    
    # Create arms
    top_arm = c << arm
    bot_arm = c << arm
    
    # Position arms vertically
    # Separation is determined by the 180-degree bend diameter (2 * radius)
    vertical_sep = 2 * bend_radius
    top_arm.movey(vertical_sep / 2)
    bot_arm.movey(-vertical_sep / 2)
    
    # Mirror bottom arm (symmetry)
    bot_arm.mirror_y()
    
    # Create Bends
    # Note: angle=180. We use the custom xs_bend which allows R=1.15
    bend_l = c << bend_euler(radius=bend_radius, angle=180, cross_section=xs_bend)
    bend_r = c << bend_euler(radius=bend_radius, angle=180, cross_section=xs_bend)
    
    # Connect Left Bend
    # top_arm.o1 is West, bot_arm.o1 is West.
    # We want bend to go from top.o1 -> curve 180 -> bot.o1
    bend_l.connect("o2", top_arm.ports["o1"])
    bend_l.connect("o1", bot_arm.ports["o1"]) 
    
    # Connect Right Bend
    # top_arm.o2 is East.
    bend_r.connect("o1", top_arm.ports["o2"])
    # bend_r.connect("o2", bot_arm.ports["o2"]) # Redundant if geometry is perfect, but ensures closure
    
    return c

if __name__ == "__main__":
    # Generate and save GDS
    device = device_racetrack_mzm_fixed()
    device.show()
    device.write_gds("racetrack_mzm_fixed.gds")