import gdsfactory as gf
import numpy as np

@gf.cell
def grating_arm(
    length=10.0,
    width=0.3,
    period=0.32,
    duty_cycle=0.5,
    layer=(1, 0)
):
    """
    Creates a straight waveguide segment consisting of periodic rectangular blocks (grating).
    Uses manual reference placement to ensure compatibility.
    """
    c = gf.Component()
    
    # Calculate dimensions
    tooth_len = period * duty_cycle
    n_teeth = int(length / period)
    
    # Create the base shape for one grating tooth
    tooth = gf.components.rectangle(size=(tooth_len, width), layer=layer, centered=True)
    
    # Place teeth using a loop (avoids add_array dependency issues)
    for i in range(n_teeth):
        ref = c << tooth
        ref.movex(i * period)
    
    # Define ports at the physical start and end of the grating structure
    # Start: Left edge of first tooth (center at 0) -> x = -tooth_len/2
    # End: Right edge of last tooth (center at (n-1)*p) -> x = (n-1)*p + tooth_len/2
    x_start = -tooth_len / 2
    x_end = (n_teeth - 1) * period + tooth_len / 2
    
    c.add_port(
        name="o1", 
        center=(x_start, 0), 
        width=width, 
        orientation=180, 
        layer=layer
    )
    c.add_port(
        name="o2", 
        center=(x_end, 0), 
        width=width, 
        orientation=0, 
        layer=layer
    )
    
    return c

@gf.cell
def hairpin_half(
    length_solid=14.0,
    length_grating=12.5,
    wg_width=0.3,
    bend_radius=0.95,
    layer=(1, 0)
):
    """
    Creates one half of the contra-DC.
    Native Orientation: Bend on Left, Arms extend Right.
    Top Arm: Solid. Bottom Arm: Grating.
    """
    c = gf.Component()
    
    # Define CrossSection with the specific bend radius to avoid validation errors
    xs = gf.cross_section.strip(width=wg_width, layer=layer, radius=bend_radius)

    # 1. Bend (Euler 180)
    # Starts at (0,0) facing East, ends at (0, 2R) facing West.
    bend = c << gf.components.bend_euler(angle=180, p=0, cross_section=xs)
    
    # 2. Solid Arm (Top)
    # Connects to bend o2 (facing West at top).
    # We want arm to extend Right (East).
    # Connect Solid o1 (West facing) to Bend o2 (West facing) -> Solid extends East.
    # Wait, 'straight' ports are: o1 (West/180), o2 (East/0).
    # connecting solid.o1 to bend.o2 places solid to the Left of bend?
    # No, connect() matches orientations. 180 mates with 0. 
    # Bend o2 is West (180). We need a port facing East (0) to mate? 
    # Actually, let's just create the straight and move it. It's simpler.
    solid = c << gf.components.straight(length=length_solid, cross_section=xs)
    # Solid o1 is at (0,0) facing 180.
    # We want Solid o1 to attach to Bend o2. 
    # Bend o2 is at (0, 2R) facing 180.
    # If we connect(solid.o1, bend.o2), gdsfactory rotates solid by 180 so solid.o1 faces 0.
    # Then solid extends East. This is what we want.
    solid.connect("o1", bend.ports["o2"])
    
    # 3. Grating Arm (Bottom)
    # Connects to bend o1 (facing East at bottom, 0,0).
    # We want Grating to extend Right (East).
    # Grating o1 faces West (180).
    # Connect Grating o1 to Bend o1. 
    # 180 mates with 0. Perfect.
    grating = c << grating_arm(length=length_grating, width=wg_width, layer=layer)
    grating.connect("o1", bend.ports["o1"])
    
    # 4. Tail (Input Taper/Bend)
    # Connects to the Right end of the Solid arm (solid.o2).
    # Solid o2 faces East (0).
    # We want a tail curving Up/Away.
    # Attach a bend. Bend o1 faces 180 (West).
    # Connect Bend o1 to Solid o2.
    # Bend curves 'Left' (positive angle) or 'Right' (negative).
    # Standard Euler curves Left (CCW). We want Up (CCW).
    # So angle=45 is correct.
    tail = c << gf.components.bend_euler(radius=2.0, angle=45, cross_section=xs)
    tail.connect("o1", solid.ports["o2"])
    
    # 5. Tip (Grating Output)
    # Connects to Right end of Grating (grating.o2).
    tip = c << gf.components.taper(length=0.8, width1=wg_width, width2=0.05, layer=layer)
    tip.connect("o1", grating.ports["o2"])
    
    return c

@gf.cell
def device_contra_dc():
    c = gf.Component()
    
    # Dimensions based on footprint ~18.24um x 0.7um
    wg_width = 0.3
    gap = 0.1
    bend_radius = 0.95
    
    # Length budget
    # We need the total length to be ~18um.
    # Structure is approx: Tail + Solid + Bend.
    # 1.5 + 14.5 + 1.0 ~ 17.0. Increasing slightly.
    l_solid = 14.8
    l_grating = 13.8 # Slightly shorter to allow tip
    
    # Create Top Hairpin (Solid Top, Grating Bottom)
    # Native orientation: Bend Left, extending Right.
    # We want: Bend Right, extending Left.
    top_hp = c << hairpin_half(
        length_solid=l_solid,
        length_grating=l_grating,
        wg_width=wg_width,
        bend_radius=bend_radius
    )
    # Rotate 180 to put bend on Right.
    # Now: Bend Right. Solid Bottom? 
    # Native: Solid Top (Y=2R). Rotated 180 -> Solid Bottom (Y=-2R).
    # This is NOT what we want for the Top device. We want Solid Top.
    # So we need to Mirror Y the native, then Rotate? Or just Mirror X?
    # Native: Bend Left, Solid Top.
    # Mirror X: Bend Right, Solid Top. Perfect.
    top_hp.mirror_x()
    
    # Create Bottom Hairpin (Grating Top, Solid Bottom)
    # We want: Bend Left, extending Right.
    # Native: Bend Left, extending Right. Solid Top.
    # We want Solid Bottom.
    # Mirror Y the Native: Bend Left, Solid Bottom. Perfect.
    bot_hp = c << hairpin_half(
        length_solid=l_solid,
        length_grating=l_grating,
        wg_width=wg_width,
        bend_radius=bend_radius
    )
    bot_hp.mirror_y()
    
    # --- Alignment ---
    
    # Vertical Separation
    # Top HP (Mirrored X): Grating is at Y=0. Solid is at Y=2R.
    # Bot HP (Mirrored Y): Grating is at Y=0. Solid is at Y=-2R.
    # We want the Gratings (both at Y=0 local) to be separated by `gap`.
    # Top Grating at +gap/2 + width/2 (center).
    # Bot Grating at -gap/2 - width/2 (center).
    # Since their local origins are the grating centers (roughly),
    # we move Top UP and Bot DOWN.
    
    dy = (wg_width + gap) / 2.0
    top_hp.movey(dy)
    bot_hp.movey(-dy)
    
    # Horizontal Overlap
    # Top HP (Bend Right): Grating extends from Right to Left.
    # Bot HP (Bend Left): Grating extends from Left to Right.
    # We want them to overlap fully.
    # Top HP X-range: [Bend_X - L, Bend_X].
    # Bot HP X-range: [Bend_X, Bend_X + L].
    # We need to shift them so the grating regions coincide.
    # Let's align their centers.
    # Top HP center x ~ -L/2.
    # Bot HP center x ~ L/2.
    # Move Top Right by L/2. Move Bot Left by L/2.
    
    overlap_shift = l_grating / 2.0
    top_hp.movex(overlap_shift)
    bot_hp.movex(-overlap_shift)
    
    return c

if __name__ == "__main__":
    device = device_contra_dc()
    device.write_gds("contra_dc.gds")