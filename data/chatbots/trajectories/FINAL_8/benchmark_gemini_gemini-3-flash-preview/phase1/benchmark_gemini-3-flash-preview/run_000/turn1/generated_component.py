import gdsfactory as gf

@gf.cell
def recreated_device():
    """
    Recreates the device geometry within a 120um x 4um footprint.
    Fixes the ValueError by defining the cross-section radius.
    """
    c = gf.Component("coupler_device")
    
    # --- Parameters ---
    total_length = 120.0
    # Radius must be small enough so (offset + radius) * 2 < 4.0um
    bend_radius = 1.2 
    straight_length = total_length - (2 * bend_radius)
    
    layer = (1, 0)
    width_thin = 0.1
    width_thick = 0.5
    pitch = 0.2
    
    # Define cross-sections with a small radius to override the 10um default
    xs_thin = gf.cross_section.cross_section(width=width_thin, layer=layer, radius=bend_radius)
    xs_thick = gf.cross_section.cross_section(width=width_thick, layer=layer, radius=bend_radius)

    # 1. Create Middle Group (5 straight waveguides)
    for i in range(-2, 3):
        y_pos = i * pitch
        mid_wg = c << gf.components.straight(length=total_length, cross_section=xs_thin)
        mid_wg.y = y_pos
        mid_wg.x = 0

    # 2. Create Side Groups (Top and Bottom)
    def add_side_bundle(y_offset_base, is_top=True):
        direction = 1 if is_top else -1
        
        # bundle consists of 1 thick and 4 thin waveguides
        # Logic: Thick line is closest to the center, thin lines are further out
        configs = [
            (width_thick, 0.0, xs_thick),
            (width_thin, 0.3, xs_thin),
            (width_thin, 0.5, xs_thin),
            (width_thin, 0.7, xs_thin),
            (width_thin, 0.9, xs_thin),
        ]
        
        for w, o, xs in configs:
            # Concentric bends: outer lines need larger radii to stay parallel
            r_local = bend_radius + o
            
            # Straight middle segment
            straight = c << gf.components.straight(length=straight_length, cross_section=xs)
            straight.y = y_offset_base + (direction * o)
            straight.x = 0
            
            # Bends at ends
            # Left side: bend upwards if top, downwards if bottom
            bl = c << gf.components.bend_euler(radius=r_local, angle=90 * direction, cross_section=xs)
            bl.connect("o1", straight.ports["o1"])
            
            # Right side: bend upwards if top, downwards if bottom
            br = c << gf.components.bend_euler(radius=r_local, angle=-90 * direction, cross_section=xs)
            br.connect("o1", straight.ports["o2"])

    # Positioning bundles so the total height remains < 4.0um
    # Max height = 2 * (y_offset_base + max_local_offset + max_r_local)
    # With y_offset=0.7, max_o=0.9, r_local=2.1 -> height is roughly 3.4um
    add_side_bundle(y_offset_base=0.7, is_top=True)
    add_side_bundle(y_offset_base=-0.7, is_top=False)

    return c

if __name__ == "__main__":
    device = recreated_device()
    device.write_gds("recreated_device.gds")
    device.show()