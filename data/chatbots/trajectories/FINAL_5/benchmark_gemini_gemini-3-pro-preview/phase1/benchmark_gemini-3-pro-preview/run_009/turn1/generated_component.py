import gdsfactory as gf

# ==============================================================================
# Parametric Settings
# ==============================================================================
LAYER_WG = (1, 0)
WIDTH_CORE = 0.5
WIDTH_TEETH = 0.8       # Wider section of the grating
GRATING_PERIOD = 0.31   # Period of the Bragg grating
DUTY_CYCLE = 0.5
GRATING_LENGTH = 18.24  # Exact length from constraints
GAP = 0.15              # Gap between the two coupled gratings
BEND_RADIUS = 2.0       # Radius for the U-turns

# ==============================================================================
# 1. Define Bragg Grating Unit Cell (Using Primitives)
# ==============================================================================
@gf.cell
def bragg_period_cell(period, w_core, w_teeth, dc):
    """
    Creates a single period of the grating using rectangle primitives.
    Avoids raw polygon coordinates.
    """
    c = gf.Component()
    
    # 1. Core Waveguide Segment (Parametric Rectangle)
    # Centered at (period/2, 0)
    core = c << gf.components.rectangle(
        size=(period, w_core), 
        layer=LAYER_WG, 
        centered=True
    )
    core.movex(period / 2.0)
    
    # 2. Grating Teeth Segment (Parametric Rectangle)
    # Overlaps the core to form the wide section
    l_teeth = period * dc
    teeth = c << gf.components.rectangle(
        size=(l_teeth, w_teeth), 
        layer=LAYER_WG, 
        centered=True
    )
    teeth.movex(period / 2.0)
    
    # Define Ports manually for this custom primitive
    c.add_port(
        name="o1", 
        center=(0, 0), 
        width=w_core, 
        orientation=180, 
        layer=LAYER_WG
    )
    c.add_port(
        name="o2", 
        center=(period, 0), 
        width=w_core, 
        orientation=0, 
        layer=LAYER_WG
    )
    
    return c

# ==============================================================================
# 2. Define Grating Arm (Array Construction)
# ==============================================================================
@gf.cell
def grating_arm(length, period, w_core, w_teeth, dc):
    c = gf.Component()
    
    # Create the unit cell once
    unit = bragg_period_cell(period, w_core, w_teeth, dc)
    n_periods = int(length / period)
    
    # Place unit cells using a loop (Robust replacement for add_array)
    for i in range(n_periods):
        ref = c << unit
        ref.movex(i * period)
        
    # Expose ports of the composite arm
    c.add_port(
        name="o1", 
        center=(0, 0), 
        width=w_core, 
        orientation=180, 
        layer=LAYER_WG
    )
    c.add_port(
        name="o2", 
        center=(n_periods * period, 0), 
        width=w_core, 
        orientation=0, 
        layer=LAYER_WG
    )
    
    return c

# ==============================================================================
# 3. Define Folded Half-Structure
# ==============================================================================
@gf.cell
def folded_coupler_half(length, radius, width):
    c = gf.Component()
    
    # FIX: Explicitly define a cross_section with the target radius.
    # This prevents the validation error "min_bend_radius < CrossSection.radius_min"
    xs = gf.cross_section.cross_section(
        width=width, 
        layer=LAYER_WG,
        radius=radius  # Set default radius to matching our tight bend
    )
    
    # 3a. Instantiate Grating Arm
    # Placed along y=0, extending from x=0 to x=length
    grating = c << grating_arm(
        length=length, 
        period=GRATING_PERIOD, 
        w_core=WIDTH_CORE, 
        w_teeth=WIDTH_TEETH, 
        dc=DUTY_CYCLE
    )
    
    # 3b. U-Bend (Euler)
    # Connects to the end of the grating (Port o2)
    # We pass 'xs' which now allows the 2.0um radius
    bend = c << gf.components.bend_euler(
        radius=radius, 
        angle=180, 
        cross_section=xs
    )
    bend.connect("o1", grating.ports["o2"])
    
    # 3c. Return Arm (Smooth Waveguide)
    # Runs parallel to grating, back towards input
    # Length = Grating Length + some extra for clearance
    return_len = length + 2.0
    return_wg = c << gf.components.straight(
        length=return_len, 
        cross_section=xs
    )
    return_wg.connect("o1", bend.ports["o2"])
    
    # 3d. Input Flare (S-bend / Curve away)
    # Curves away from the device axis
    flare = c << gf.components.bend_euler(
        radius=radius, 
        angle=-45, 
        cross_section=xs
    )
    flare.connect("o1", return_wg.ports["o2"])
    
    # Expose useful ports
    # Port for external connection (flare end)
    c.add_port("io", port=flare.ports["o2"])
    # Port for alignment reference (grating start)
    c.add_port("coupling_ref", port=grating.ports["o1"])
    
    return c

# ==============================================================================
# 4. Final Device Assembly
# ==============================================================================
@gf.cell
def contra_directional_coupler():
    c = gf.Component()
    
    # Instantiate Top Half
    top = c << folded_coupler_half(
        length=GRATING_LENGTH, 
        radius=BEND_RADIUS, 
        width=WIDTH_CORE
    )
    
    # Instantiate Bottom Half
    bottom = c << folded_coupler_half(
        length=GRATING_LENGTH, 
        radius=BEND_RADIUS, 
        width=WIDTH_CORE
    )
    
    # Rotate Bottom Half 180 degrees
    bottom.rotate(180)
    
    # --- Alignment Calculation ---
    # We want the 'teeth' edges to be separated by GAP.
    # The grating axis is at local y=0 for both components.
    # The grating width is WIDTH_TEETH.
    # Distance between centerlines = (WIDTH_TEETH/2) + GAP + (WIDTH_TEETH/2)
    center_dy = WIDTH_TEETH + GAP
    
    # Shift Top up and Bottom down
    top.movey(center_dy / 2.0)
    bottom.movey(-center_dy / 2.0)
    
    # X-Alignment
    # Top grating: x=0 to x=L
    # Bottom grating (after 180 rot): x=0 to x=-L
    # We must shift bottom by +L so they overlap perfectly from 0 to L
    bottom.movex(GRATING_LENGTH)
    
    return c

# ==============================================================================
# Execution
# ==============================================================================
if __name__ == "__main__":
    device = contra_directional_coupler()
    device.write_gds("contra_directional_coupler.gds")
    # gf.show(device)