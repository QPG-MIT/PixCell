import gdsfactory as gf
import numpy as np

@gf.cell
def device_120_4():
    """
    Parametric recreation of the symmetric waveguide structure.
    Footprint: 120um x 4um.
    Features: 
    - Central bus of 5 waveguides.
    - Top/Bottom tapered wings with internal slots (ladder structure).
    - Constant width side rails on the wings following a sine taper.
    """
    c = gf.Component()
    
    # --- Dimensions & Constants ---
    total_len = 120.0
    layer_core = (1, 0)
    
    # --- Vertical Budgeting (Target Height = 4.0um) ---
    # We have high feature density. We allocate vertical space carefully.
    # Central Bus: 5 lines, 4 gaps
    # Wings: 2 wings (each has alternating bars and slots)
    
    line_w = 0.15
    gap_w = 0.15
    
    # Central Bus Config
    n_bus = 5
    # Height of central bus = 5 lines + 4 gaps
    h_bus = n_bus * line_w + (n_bus - 1) * gap_w  # 0.75 + 0.60 = 1.35 um
    
    # Wing Config
    # Wing pattern: Bar - Slot - Bar - Slot - Bar - Slot - Bar
    # 4 Bars + 3 Slots
    n_wing_slots = 3
    n_wing_bars = 4
    h_wing = n_wing_bars * line_w + n_wing_slots * gap_w # 0.60 + 0.45 = 1.05 um
    
    # Spacing Calculation
    # Total occupied vertical space = Bus + 2*Wings = 1.35 + 2.1 = 3.45 um
    # Remaining space for isolation gaps = 4.0 - 3.45 = 0.55 um
    # Gap per side = 0.275 um
    bus_wing_gap = 0.275
    
    # Wing Geometry Parameters
    wing_w_base = 120.0  # Full width at the center (matches device width)
    wing_w_tip = 112.0   # Width at the outer edge (tapered in)
    rail_w = 1.5         # Width of the solid side rails

    # --- 1. Central Bus Construction ---
    # Create the 5 parallel waveguides centered at y=0
    xs_bus = gf.cross_section.cross_section(width=line_w, layer=layer_core)
    wg_straight = gf.components.straight(length=total_len, cross_section=xs_bus)
    
    # Calculate starting Y to center the group
    y_start_bus = -h_bus / 2 + line_w / 2
    for i in range(n_bus):
        ref = c << wg_straight
        ref.x = 0
        ref.y = y_start_bus + i * (line_w + gap_w)

    # --- 2. Wing Generator Function ---
    def create_wing_shape():
        """
        Creates the wing component using manual polygon construction.
        This allows us to match the slot lengths exactly to the outer tapered profile.
        """
        # Define the taper profile function (half-width vs y)
        # y goes from 0 (base, near bus) to h_wing (tip, outer edge)
        def get_half_width(y):
            # Normalized coordinate [0, 1]
            frac = y / h_wing
            # Sine taper profile for smooth curve
            delta = (wing_w_base - wing_w_tip) / 2
            offset = delta * np.sin(frac * np.pi / 2)
            return (wing_w_base / 2) - offset

        # A. Create Outer Envelope (The solid background shape)
        # We generate a polygon by sampling points along the curve
        num_pts = 60
        y_vals = np.linspace(0, h_wing, num_pts)
        right_edge = [(get_half_width(y), y) for y in y_vals]
        # Mirror right edge to get left edge (reversed to close loop)
        left_edge = [(-x, y) for x, y in reversed(right_edge)]
        envelope_pts = right_edge + left_edge
        
        envelope_cmp = gf.Component()
        envelope_cmp.add_polygon(envelope_pts, layer=layer_core)
        
        # B. Create Slots (Negative space to subtract)
        slots_layer = gf.Component()
        
        # Slots are positioned in the gaps between bars
        # Pattern starts with a Bar at y=0.
        # First slot center Y = line_w + gap_w/2
        for i in range(n_wing_slots):
            y_slot_center = line_w + gap_w/2 + i * (line_w + gap_w)
            
            # Calculate required slot length to maintain constant rail width
            # Slot Width = Total Envelope Width at this Y - 2 * Rail Width
            w_env = 2 * get_half_width(y_slot_center)
            w_slot = w_env - 2 * rail_w
            
            if w_slot > 0:
                s = slots_layer << gf.components.rectangle(
                    size=(w_slot, gap_w), 
                    layer=layer_core, 
                    centered=True
                )
                s.y = y_slot_center
                s.x = 0
        
        # C. Boolean Subtract
        # Cut the slots out of the envelope
        return gf.boolean(envelope_cmp, slots_layer, operation="not", layer=layer_core)

    # --- 3. Place Wings ---
    wing_final = create_wing_shape()
    
    # Place Top Wing
    top_ref = c << wing_final
    top_ref.ymin = h_bus / 2 + bus_wing_gap
    top_ref.x = 0
    
    # Place Bottom Wing (Mirrored)
    bot_ref = c << wing_final
    bot_ref.mirror(p1=(0,0), p2=(1,0)) # Mirror vertically across X-axis
    bot_ref.ymax = -(h_bus / 2 + bus_wing_gap)
    bot_ref.x = 0
    
    return c

# Generate and save
device = device_120_4()
device.write_gds("device_120_4.gds")