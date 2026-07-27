import gdsfactory as gf
import numpy as np

# ==============================================================================
# Parametric Settings
# ==============================================================================
LENGTH_GRATING = 18.24
WIDTH_CORE = 0.5
PERIOD = 0.318
DUTY_CYCLE = 0.5
TOOTH_DEPTH = 0.15    # Depth of the grating corrugations
GAP = 0.15            # Coupling gap between teeth tips
RADIUS = 1.5          # Bend radius
SBEND_L = 5.0         # Horizontal length of flares
SBEND_H = 1.0         # Vertical offset of flares
LAYER_WG = (1, 0)

# ==============================================================================
# 1. Custom Components
# ==============================================================================

@gf.cell
def grating_waveguide(
    length=10.0,
    width=0.5,
    period=0.318,
    dc=0.5,
    tooth_depth=0.15,
    teeth_location="bottom",  # "top", "bottom", "both"
    layer=(1, 0)
):
    """
    Straight waveguide with periodic rectangular teeth.
    """
    c = gf.Component()
    
    # 1. Core Waveguide
    # Centered at y=0 locally
    core = c << gf.components.rectangle(size=(length, width), layer=layer)
    core.movey(-width/2)
    
    # 2. Teeth Generation
    # Create a single tooth polygon to reference
    tooth_len = period * dc
    tooth = gf.components.rectangle(size=(tooth_len, tooth_depth), layer=layer)
    
    num_teeth = int(length / period)
    
    # Loop to place references
    # We use range(num_teeth) to place them periodically
    for i in range(num_teeth):
        x_pos = i * period
        
        # Add Top Teeth
        if teeth_location in ["top", "both"]:
            t = c << tooth
            # Place on top edge: y = width/2
            t.move((x_pos, width/2))
            
        # Add Bottom Teeth
        if teeth_location in ["bottom", "both"]:
            t = c << tooth
            # Place on bottom edge: y = -width/2 - tooth_depth
            t.move((x_pos, -width/2 - tooth_depth))
            
    # 3. Ports
    c.add_port("o1", center=(0, 0), width=width, orientation=180, layer=layer)
    c.add_port("o2", center=(length, 0), width=width, orientation=0, layer=layer)
    
    return c

@gf.cell
def folded_coupler_half(
    length=18.24,
    width=0.5,
    period=0.318,
    tooth_depth=0.15,
    gap=0.2,
    radius=1.5,
    sbend_size=(-5.0, 1.0), # (dx, dy) for the flare. Negative dx = Left.
    inner_teeth_loc="bottom" # "bottom" for top half, "top" for bottom half
):
    """
    Creates the folded arm structure:
    - Inner straight arm (grating)
    - U-turn
    - Outer straight arm (smooth)
    - S-bend flares on the input side (Left)
    """
    c = gf.Component()
    xs = gf.cross_section.cross_section(width=width, layer=LAYER_WG, radius=radius)
    
    # 1. Inner Grating Arm
    # Placed at y=0
    g_arm = c << grating_waveguide(
        length=length,
        width=width,
        period=period,
        tooth_depth=tooth_depth,
        teeth_location=inner_teeth_loc,
        layer=LAYER_WG
    )
    
    # 2. U-Bend (Right Side)
    # Connects Inner Arm (o2) -> Outer Arm
    # Using circular bend to match the "perfect U" look of the target
    bend = c << gf.components.bend_circular(
        angle=180,
        radius=radius,
        cross_section=xs
    )
    bend.connect("o1", g_arm.ports["o2"])
    
    # 3. Outer Return Arm (Smooth)
    # Runs back from Right to Left
    return_wg = c << gf.components.straight(length=length, cross_section=xs)
    return_wg.connect("o1", bend.ports["o2"])
    
    # 4. Input S-Bend Flares (Left Side)
    # We want the waveguides to flare AWAY from the central bus.
    # sbend_size should be passed appropriately (negative x, +/- y).
    
    # Inner Arm Flare
    flare_inner = c << gf.components.bend_s(size=sbend_size, cross_section=xs)
    flare_inner.connect("o1", g_arm.ports["o1"])
    
    # Outer Arm Flare
    # We use the same shape flare, attached to the return waveguide end.
    # Since return_wg is shifted in Y by 2*radius, this flare preserves parallelism relative to the inner one.
    flare_outer = c << gf.components.bend_s(size=sbend_size, cross_section=xs)
    flare_outer.connect("o1", return_wg.ports["o2"])
    
    # Expose ports
    c.add_port("in_inner", port=flare_inner.ports["o2"])
    c.add_port("in_outer", port=flare_outer.ports["o2"])
    
    return c

# ==============================================================================
# 2. Final Device Assembly
# ==============================================================================

@gf.cell
def contra_directional_coupler():
    c = gf.Component()
    
    # Derived Dimensions
    # Calculate Y-offset to achieve the desired coupling gap.
    # Bus (center y=0): Half-width (w/2) + Tooth (d) -> Edge at w/2 + d
    # Arm (center y=Y): Half-width (w/2) + Tooth (d) -> Edge at Y - (w/2 + d)
    # Gap condition: (Y - w/2 - d) - (w/2 + d) = GAP
    # Y = 2*(w/2 + d) + GAP = w + 2*d + GAP
    y_offset = WIDTH_CORE + 2*TOOTH_DEPTH + GAP
    
    # 1. Central Bus (Grating on BOTH sides)
    # Matches the visual texture of the central bar in the target
    bus = c << grating_waveguide(
        length=LENGTH_GRATING,
        width=WIDTH_CORE,
        period=PERIOD,
        tooth_depth=TOOTH_DEPTH,
        teeth_location="both",
        layer=LAYER_WG
    )
    bus.x = 0
    bus.y = 0
    
    # 2. Top Folded Structure
    # Inner teeth on BOTTOM (facing bus). Flares go UP (positive Y) and LEFT.
    top = c << folded_coupler_half(
        length=LENGTH_GRATING,
        width=WIDTH_CORE,
        period=PERIOD,
        tooth_depth=TOOTH_DEPTH,
        gap=GAP,
        radius=RADIUS,
        sbend_size=(-SBEND_L, SBEND_H), # Go Left (-5) and Up (+1)
        inner_teeth_loc="bottom"
    )
    top.movey(y_offset)
    
    # 3. Bottom Folded Structure
    # Inner teeth on TOP (facing bus). Flares go DOWN (negative Y) and LEFT.
    bot = c << folded_coupler_half(
        length=LENGTH_GRATING,
        width=WIDTH_CORE,
        period=PERIOD,
        tooth_depth=TOOTH_DEPTH,
        gap=GAP,
        radius=RADIUS,
        sbend_size=(-SBEND_L, -SBEND_H), # Go Left (-5) and Down (-1)
        inner_teeth_loc="top"
    )
    bot.movey(-y_offset)
    
    # Ports
    c.add_port("o1", port=bus.ports["o1"])
    c.add_port("o2", port=bus.ports["o2"])
    c.add_port("top_in", port=top.ports["in_inner"])
    c.add_port("bot_in", port=bot.ports["in_inner"])

    return c

if __name__ == "__main__":
    device = contra_directional_coupler()
    device.write_gds("contra_directional_coupler.gds")