import gdsfactory as gf
import numpy as np

@gf.cell
def device_120_4():
    """
    Parametric reproduction of the coupled waveguide grating device.
    Features a central straight grating and outer flared sections with slots.
    Constrained to 120um x 4um footprint.
    """
    c = gf.Component()

    # ==========================================
    # 1. Define Parameters
    # ==========================================
    # Footprint constraints
    L_outer = 120.0     # Max width at outer edges
    H_total = 4.0       # Total vertical height
    
    # Geometric Parameters estimated from visual target
    L_inner = 94.0      # Width of the central straight section (start of flare)
    
    # Central Grating (5 lines)
    n_center = 5
    w_center = 0.20     # Line width
    g_center = 0.14     # Gap width
    
    # Calculate height of central bundle
    h_center_bundle = n_center * w_center + (n_center - 1) * g_center
    
    # Gap between central bundle and outer horns
    gap_main = 0.18
    
    # Horn section parameters
    # Calculate available height for one horn
    # H_total = h_center_bundle + 2*gap_main + 2*h_horn
    h_horn = (H_total - h_center_bundle - 2 * gap_main) / 2
    
    # Horn internal slot configuration 
    # Pattern derived from image: Bar(Med) -> Gap -> Bar(Thin) -> Gap -> Bar(Thick/Remainder)
    h_slot = 0.11
    h_bar1 = 0.23       # Inner bar height
    h_bar2 = 0.14       # Middle bar height
    
    layer = (1, 0)

    # ==========================================
    # 2. Build Central Grating
    # ==========================================
    # Center bundle is centered at y=0
    center_comp = gf.Component()
    y_start_center = -h_center_bundle / 2 + w_center / 2
    
    for i in range(n_center):
        y = y_start_center + i * (w_center + g_center)
        # Straight waveguides/rectangles
        rect = center_comp << gf.components.rectangle(size=(L_inner, w_center), layer=layer, centered=True)
        rect.movey(y)
    
    c << center_comp

    # ==========================================
    # 3. Build Tapered Horn with Slots
    # ==========================================
    # Create the tapered shape using path extrusion
    # Align path along Y so width varies along X
    path = gf.Path([(0, 0), (0, h_horn)])
    
    # Cross Sections: Width transitions from L_inner to L_outer
    xs_inner = gf.cross_section.cross_section(width=L_inner, layer=layer)
    xs_outer = gf.cross_section.cross_section(width=L_outer, layer=layer)
    
    # Transition profile (Sine for smooth S-curve expansion)
    transition = gf.path.transition(xs_inner, xs_outer, width_type='sine')
    
    # Extrude to create the solid horn block
    horn_solid = gf.path.extrude_transition(path, transition)
    
    # Create slots to subtract
    slots_comp = gf.Component()
    
    # Position slots relative to horn start (y=0)
    y_slot1 = h_bar1 + h_slot/2
    y_slot2 = h_bar1 + h_slot + h_bar2 + h_slot/2
    
    slot_width = L_outer + 10.0 # Oversized to ensure full cut
    
    s1 = slots_comp << gf.components.rectangle(size=(slot_width, h_slot), layer=layer, centered=True)
    s1.movey(y_slot1)
    
    s2 = slots_comp << gf.components.rectangle(size=(slot_width, h_slot), layer=layer, centered=True)
    s2.movey(y_slot2)
    
    # Boolean subtraction: Horn - Slots
    horn_final = gf.boolean(horn_solid, slots_comp, operation='not', layer=layer)

    # ==========================================
    # 4. Place Horns
    # ==========================================
    y_horn_offset = h_center_bundle / 2 + gap_main
    
    # Top Horn (Original orientation)
    top_horn = c << horn_final
    top_horn.movey(y_horn_offset)
    
    # Bottom Horn (Mirrored and moved)
    # Mirroring across X maintains the "narrow at center, wide at outside" orientation
    bot_horn = c << horn_final
    bot_horn.mirror(p1=(0,0), p2=(1,0)) # Mirror across X axis
    bot_horn.movey(-y_horn_offset)
    
    return c

# Generate and save
if __name__ == "__main__":
    device = device_120_4()
    device.write_gds("device.gds")