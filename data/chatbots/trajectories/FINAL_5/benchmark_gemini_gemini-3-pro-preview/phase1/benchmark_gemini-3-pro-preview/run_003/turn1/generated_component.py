import gdsfactory as gf

@gf.cell
def contra_directional_coupler_loops():
    """
    Parametric recreation of a Contra-Directional Coupler with loopback paths.
    
    Includes:
    - Central grating region with periodic teeth.
    - Euler bends for adiabatic 180-degree turns.
    - S-bend flares for input/output ports.
    """
    c = gf.Component()

    # --- 1. Parameters ---
    # Dimensions derived to match the ~18.24um length constraint and visual proportions
    L_grating = 13.5        # Length of the active coupling region
    period = 0.32           # Grating period
    duty_cycle = 0.5        # Duty cycle of the teeth
    teeth_depth = 0.15      # Depth of the corrugations extending into the gap
    wg_width = 0.45         # Width of the waveguide core
    gap = 0.15              # Minimum gap distance between the tips of the teeth
    bend_radius = 2.2       # Radius for the 180-degree return loops
    flare_radius = 5.0      # Radius for the input/output flares
    flare_angle = 30.0      # Angle for the flares

    # Layer definition
    layer_wg = (1, 0)
    
    # FIX: Explicitly set radius in cross_section to allow tight bends (prevents ValueError)
    xs = gf.cross_section.cross_section(
        width=wg_width, 
        layer=layer_wg, 
        radius=bend_radius
    )

    # Vertical offsets
    # The structure is symmetric around y=0.
    y_core_offset = (gap / 2) + teeth_depth + (wg_width / 2)

    # --- 2. Helper Components ---

    # Define the tooth primitive
    tooth = gf.components.rectangle(
        size=(period * duty_cycle, teeth_depth), 
        layer=layer_wg, 
        centered=False
    )

    def make_grated_arm(length, y_pos, teeth_direction):
        """
        Creates a straight waveguide with periodic teeth.
        teeth_direction: -1 for teeth pointing down, 1 for teeth pointing up.
        """
        arm = gf.Component()
        
        # Main waveguide core
        core = arm << gf.components.straight(length=length, cross_section=xs)
        core.movey(y_pos)
        
        # Expose ports of the core for easy connection later
        arm.add_port("o1", port=core.ports["o1"])
        arm.add_port("o2", port=core.ports["o2"])
        
        # Add periodic teeth
        n_teeth = int(length / period)
        for i in range(n_teeth):
            t = arm << tooth
            # Calculate Y position for the tooth
            if teeth_direction == -1: # Pointing Down (Top Arm)
                y_base = y_pos - wg_width/2
                # Rectangle drawn from bottom-left. Move top to y_base.
                t.move((i * period, y_base - teeth_depth))
            else: # Pointing Up (Bottom Arm)
                y_base = y_pos + wg_width/2
                # Rectangle sits on top of this line
                t.move((i * period, y_base))
                
        return arm

    # --- 3. Construct Geometry ---

    # Create Top and Bottom Grating Arms
    top_grating = c << make_grated_arm(L_grating, y_core_offset, teeth_direction=-1)
    bot_grating = c << make_grated_arm(L_grating, -y_core_offset, teeth_direction=1)

    # Define common bend and straight components
    # 180 degree bend for the loops
    bend_180 = gf.components.bend_euler(radius=bend_radius, angle=180, cross_section=xs)
    # Return waveguide
    wg_return = gf.components.straight(length=L_grating + bend_radius, cross_section=xs)
    # Input/Output flare bend
    flare_bend = gf.components.bend_euler(radius=flare_radius, angle=flare_angle, cross_section=xs)

    # -- Top Loop Assembly --
    # 1. Bend: Connects to the RIGHT end ("o2") of the top grating
    # Standard bend curves "Left". Relative to East-facing port, it curves North (Up).
    # Since we are connecting to top_grating.o2 (facing East), a standard bend 
    # connected via `o1` (facing West) will be rotated 180.
    # A standard bend rotated 180 curves South. We want North (Up).
    # So we must Mirror the bend.
    top_bend = c << bend_180
    top_bend.mirror()
    top_bend.connect("o1", top_grating.ports["o2"])
    
    # 2. Return Path
    top_return = c << wg_return
    top_return.connect("o1", top_bend.ports["o2"])

    # 3. Input Flare (Top Left)
    # Connects to top_grating.o1 (facing West).
    # We want it to curve North (Up).
    # Standard bend connected to West port rotates 0? 
    # No, o1 is West (180), bend o1 is West (180). They don't oppose. 
    # Bend rotates 180 -> o1 faces East.
    # Bend curves North. 
    # Wait, simple mirroring is safer to visualize.
    # We want a curve going Up/Left.
    top_flare = c << flare_bend
    top_flare.mirror() 
    top_flare.connect("o1", top_grating.ports["o1"])

    # -- Bottom Loop Assembly --
    # 1. Bend: Connects to the LEFT end ("o1") of the bottom grating
    # We want it to curve South (Down).
    # bot_grating.o1 faces West.
    # Connect bend o1 (West). Rotates 180 -> Faces East.
    # Standard bend curves North. We want South.
    # Mirror.
    bot_bend = c << bend_180
    bot_bend.mirror()
    bot_bend.connect("o1", bot_grating.ports["o1"])
    
    # 2. Return Path
    bot_return = c << wg_return
    bot_return.connect("o1", bot_bend.ports["o2"])

    # 3. Output Flare (Bottom Right)
    # Connects to bot_grating.o2 (facing East).
    # We want it to curve South (Down).
    # Connect bend o1 (West). Opposes. No rotation.
    # Standard bend curves North. We want South.
    # Mirror.
    bot_flare = c << flare_bend
    bot_flare.mirror()
    bot_flare.connect("o1", bot_grating.ports["o2"])

    return c

if __name__ == "__main__":
    device = contra_directional_coupler_loops()
    device.write_gds("cdc_recreation.gds")
    device.show()