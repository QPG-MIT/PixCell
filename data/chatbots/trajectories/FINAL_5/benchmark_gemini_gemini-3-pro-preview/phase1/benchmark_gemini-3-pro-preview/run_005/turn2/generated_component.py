import gdsfactory as gf

@gf.cell
def grating_arm(
    length=12.0,
    width=0.22,
    tooth_depth=0.12,
    pitch=0.26,
    fill_factor=0.5,
    layer=(1, 0)
):
    """
    Creates a waveguide backbone with grating teeth protruding from one side.
    """
    c = gf.Component()
    
    # 1. Main Waveguide Backbone
    # Explicitly draw the core rectangle centered at y=0
    backbone = c << gf.components.rectangle(size=(length, width), layer=layer, centered=False)
    backbone.movey(-width/2) # Center vertically around y=0
    
    # 2. Grating Teeth
    tooth_width = pitch * fill_factor
    # Create the tooth shape
    tooth = gf.components.rectangle(size=(tooth_width, tooth_depth), layer=layer, centered=True)
    
    n_teeth = int(length // pitch)
    
    # Teeth attach to the bottom edge of the backbone (y = -width/2)
    # The tooth center must be shifted so its top edge overlaps the backbone bottom edge
    # Tooth top = y_center + depth/2. We want Tooth top = -width/2 + overlap
    overlap = 0.005 # Small overlap to ensure connectivity in rendering/GDS
    y_tooth = -width/2 - tooth_depth/2 + overlap
    
    for i in range(n_teeth):
        x = i * pitch + pitch/2
        t = c << tooth
        t.move((x, y_tooth))
        
    # Define ports for connection
    c.add_port("o1", center=(0, 0), width=width, orientation=180, layer=layer)
    c.add_port("o2", center=(length, 0), width=width, orientation=0, layer=layer)
    
    return c

@gf.cell
def loop_structure(
    length=12.0,
    width=0.22,
    tooth_depth=0.12,
    pitch=0.26,
    radius=1.5,
    layer=(1, 0)
):
    """
    Assembles one half of the device: Input Flare -> Grating -> Loop -> Return Taper.
    """
    c = gf.Component()
    
    # Custom cross-section for the bends (allows tighter radii than default)
    xs = gf.cross_section.cross_section(width=width, layer=layer, radius_min=0.5)

    # 1. Grating Arm (Interaction Region)
    grating = c << grating_arm(
        length=length,
        width=width,
        tooth_depth=tooth_depth,
        pitch=pitch,
        layer=layer
    )
    
    # 2. Hairpin Loop (180 degree bend)
    bend = c << gf.components.bend_euler(
        radius=radius,
        angle=180,
        cross_section=xs
    )
    bend.connect("o1", grating.ports["o2"])
    
    # 3. Return Arm (Straight section)
    return_arm = c << gf.components.straight(
        length=length,
        cross_section=xs
    )
    return_arm.connect("o1", bend.ports["o2"])
    
    # 4. Input Flare
    # Curves "up" and away from the central bus.
    # Relative to port o1 (facing West), a "Right" turn (negative angle) curves North (Up).
    flare_in = c << gf.components.bend_euler(
        radius=radius*1.5,
        angle=-30, 
        cross_section=xs
    )
    flare_in.connect("o1", grating.ports["o1"])
    
    # 5. Output Taper
    # Tapers the return arm to a sharp point
    taper = c << gf.components.taper(
        length=2.0,
        width1=width,
        width2=0.04, # Sharp tip
        layer=layer
    )
    taper.connect("o1", return_arm.ports["o2"])
    
    return c

@gf.cell
def contra_dc_device():
    """
    Full assembly of the Contra-Directional Coupler.
    """
    c = gf.Component()
    
    # --- Dimensions ---
    # Total length matches ~18um constraint.
    # Widths are minimized to match the visual ratio (thin bus, visible teeth).
    L_grating = 11.5
    W_bus = 0.12        # Very thin central bus
    W_arm = 0.22        # Grating waveguide width
    Gap = 0.10          # Gap between teeth and bus
    Tooth_depth = 0.12  # Height of the teeth
    Pitch = 0.26        # Grating period
    Radius = 1.0        # Bend radius
    
    layer = (1, 0)
    xs_bus = gf.cross_section.cross_section(width=W_bus, layer=layer)
    
    # 1. Central Bus Waveguide
    bus_len = L_grating + 6.0
    bus = c << gf.components.straight(length=bus_len, cross_section=xs_bus)
    bus.center = (0, 0)
    
    # Calculate Y-offset
    # We need the tip of the grating teeth to be exactly 'Gap' away from the bus edge.
    # Bus Edge y = W_bus / 2
    # Target Tooth Tip y = W_bus / 2 + Gap
    # The 'grating_arm' component is centered at its backbone y=0. Teeth extend down to: -W_arm/2 - Tooth_depth.
    # So we place the component at y_offset such that:
    # y_offset + (-W_arm/2 - Tooth_depth) = Target Tooth Tip y
    y_offset = (W_bus / 2 + Gap) + (W_arm / 2 + Tooth_depth)
    
    # 2. Top Loop Structure
    top = c << loop_structure(
        length=L_grating,
        width=W_arm,
        tooth_depth=Tooth_depth,
        pitch=Pitch,
        radius=Radius,
        layer=layer
    )
    # Center horizontally relative to the grating section
    top.movex(-L_grating/2)
    top.movey(y_offset)
    
    # 3. Bottom Loop Structure
    # Create identical structure and rotate 180 degrees
    bot = c << loop_structure(
        length=L_grating,
        width=W_arm,
        tooth_depth=Tooth_depth,
        pitch=Pitch,
        radius=Radius,
        layer=layer
    )
    bot.rotate(180)
    
    # Align Bottom Structure
    # After rotation, the grating runs 0 to -L. Center is at -L/2.
    # We move X by +L/2 to center it at 0.
    bot.movex(L_grating/2)
    # After rotation, Y flips. We simply move it to negative offset.
    bot.movey(-y_offset)
    
    return c

if __name__ == "__main__":
    device = contra_dc_device()
    device.write_gds("contra_dc.gds")
    device.show()