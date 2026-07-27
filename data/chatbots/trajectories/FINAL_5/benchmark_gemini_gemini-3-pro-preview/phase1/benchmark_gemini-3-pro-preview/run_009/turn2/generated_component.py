import gdsfactory as gf

# ==============================================================================
# Parametric Settings
# ==============================================================================
LAYER_WG = (1, 0)
WIDTH_CORE = 0.5        # Width of the solid waveguide backbone
TOOTH_DEPTH = 0.15      # How far the grating teeth stick out
GRATING_PERIOD = 0.31   # Bragg period
DUTY_CYCLE = 0.5
GRATING_LENGTH = 18.24  # Total length of the grating section
GAP = 0.15              # Coupling gap between the teeth tips
BEND_RADIUS = 2.0       # Radius for the U-turns

# ==============================================================================
# 1. Define Asymmetric Grating Arm
# ==============================================================================
@gf.cell
def grating_arm_asymmetric(length, period, w_core, tooth_depth, dc):
    """
    Creates a straight waveguide with grating teeth on ONE side (bottom).
    """
    c = gf.Component()
    
    # 1. Continuous Backbone (Prevents gaps in rendering)
    # Using a simple rectangle for the full length ensures continuity
    core = c << gf.components.rectangle(
        size=(length, w_core),
        layer=LAYER_WG,
        centered=False
    )
    # Center the core vertically at y=0, starts at x=0
    core.movey(-w_core / 2.0)
    
    # 2. Add Teeth (Corrugations) on the BOTTOM edge
    # The teeth will extend from y = -w_core/2 down to y = -w_core/2 - tooth_depth
    n_periods = int(length / period)
    tooth_len = period * dc
    
    # Create one tooth primitive
    tooth_poly = gf.components.rectangle(
        size=(tooth_len, tooth_depth),
        layer=LAYER_WG,
        centered=False
    )
    
    # Place teeth in a loop
    for i in range(n_periods):
        t = c << tooth_poly
        # X position: start of period + offset
        x_pos = i * period
        # Y position: aligned to bottom edge of core, extending down
        y_pos = -w_core / 2.0 - tooth_depth
        t.move((x_pos, y_pos))

    # Add Ports
    c.add_port("o1", center=(0, 0), width=w_core, orientation=180, layer=LAYER_WG)
    c.add_port("o2", center=(length, 0), width=w_core, orientation=0, layer=LAYER_WG)
    
    return c

# ==============================================================================
# 2. Define Folded Half-Structure
# ==============================================================================
@gf.cell
def folded_coupler_half(length, radius, width, tooth_depth):
    c = gf.Component()
    
    # Define generic cross-section for bends/straights (no grating)
    xs = gf.cross_section.cross_section(
        width=width, 
        layer=LAYER_WG,
        radius=radius
    )
    
    # 2a. Instantiate Grating Arm
    grating = c << grating_arm_asymmetric(
        length=length, 
        period=GRATING_PERIOD, 
        w_core=width, 
        tooth_depth=tooth_depth, 
        dc=DUTY_CYCLE
    )
    
    # 2b. U-Bend (Euler)
    # Connects to the output of the grating
    bend = c << gf.components.bend_euler(
        radius=radius, 
        angle=180, 
        cross_section=xs
    )
    bend.connect("o1", grating.ports["o2"])
    
    # 2c. Return Arm (Smooth Waveguide)
    # Returns parallel to the grating. 
    # Length needs to account for the bend displacement to bring ports somewhat aligned,
    # but strictly it just needs to go back.
    return_len = length + radius
    return_wg = c << gf.components.straight(
        length=return_len, 
        cross_section=xs
    )
    return_wg.connect("o1", bend.ports["o2"])
    
    # 2d. Input Flare (S-bend / Curve away)
    flare = c << gf.components.bend_euler(
        radius=radius, 
        angle=-45, 
        cross_section=xs
    )
    flare.connect("o1", return_wg.ports["o2"])
    
    # Ports
    c.add_port("io", port=flare.ports["o2"])
    c.add_port("coupling_ref", port=grating.ports["o1"])
    
    return c

# ==============================================================================
# 3. Final Device Assembly
# ==============================================================================
@gf.cell
def contra_directional_coupler():
    c = gf.Component()
    
    # 3a. Create Top Half
    # Teeth are on the BOTTOM of the grating arm.
    top = c << folded_coupler_half(
        length=GRATING_LENGTH, 
        radius=BEND_RADIUS, 
        width=WIDTH_CORE,
        tooth_depth=TOOTH_DEPTH
    )
    
    # 3b. Create Bottom Half
    # Identical component
    bottom = c << folded_coupler_half(
        length=GRATING_LENGTH, 
        radius=BEND_RADIUS, 
        width=WIDTH_CORE,
        tooth_depth=TOOTH_DEPTH
    )
    
    # 3c. Rotate Bottom Half
    # When rotated 180, the "bottom" teeth will now be on "top", facing the top arm.
    bottom.rotate(180)
    
    # 3d. Alignment
    # We want the tips of the teeth to be separated by GAP.
    # Top Arm: Center Y=0. Teeth edge = -WIDTH_CORE/2 - TOOTH_DEPTH
    # Bottom Arm (Rotated): Center Y=0. Teeth edge = +WIDTH_CORE/2 + TOOTH_DEPTH
    
    # We need to shift them apart vertically.
    # Target Y for Top Teeth Tip = GAP / 2
    # Current Y for Top Teeth Tip = -WIDTH_CORE/2 - TOOTH_DEPTH
    # Shift = GAP/2 - (-WIDTH_CORE/2 - TOOTH_DEPTH) = GAP/2 + WIDTH_CORE/2 + TOOTH_DEPTH
    
    y_shift = (GAP + WIDTH_CORE)/2.0 + TOOTH_DEPTH
    
    top.movey(y_shift)
    bottom.movey(-y_shift) # Symmetric spacing
    
    # X Alignment
    # Bottom arm is rotated 180, so it extends from 0 to -L.
    # We need to move it by +L to overlap with the Top arm (0 to L).
    bottom.movex(GRATING_LENGTH)
    
    return c

# ==============================================================================
# Execution
# ==============================================================================
if __name__ == "__main__":
    device = contra_directional_coupler()
    device.write_gds("contra_directional_coupler.gds")