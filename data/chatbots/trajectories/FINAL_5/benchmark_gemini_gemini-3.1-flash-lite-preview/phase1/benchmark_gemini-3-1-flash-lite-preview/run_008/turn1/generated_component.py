import gdsfactory as gf

@gf.cell
def device_geometry():
    c = gf.Component()
    
    # FIX: Define a custom cross-section with a small radius.
    # This overrides the default 'strip' radius restriction (5.0um).
    xs = gf.cross_section.cross_section(
        width=0.05, 
        radius=0.2, 
        layer=(1, 0)
    )
    
    # 1. Central Backbone
    length = 18.24
    spine = c << gf.components.straight(length=length, cross_section=xs)
    
    # 2. Periodic Fingers (Manual loop to avoid array errors)
    finger_template = gf.components.rectangle(size=(0.04, 0.2), layer=(1, 0), centered=True)
    num_fingers = 60
    spacing = length / num_fingers
    
    for i in range(num_fingers):
        x_pos = i * spacing
        
        # Add Top Finger
        f_top = c << finger_template
        f_top.move((x_pos, 0.25))
        
        # Add Bottom Finger
        f_bot = c << finger_template
        f_bot.move((x_pos, -0.25))

    # 3. U-Shape Structures
    # Creates: [Bend 180] -> [Straight] -> [Taper]
    def create_hook(mirror=False):
        hook = gf.Component()
        
        # Bend to turn 180 degrees
        bend = hook << gf.components.bend_euler(radius=0.2, angle=180, cross_section=xs)
        
        # Straight part
        straight = hook << gf.components.straight(length=length - 0.4, cross_section=xs)
        straight.connect("o1", bend.ports["o2"])
        
        # Taper to point (width decreases)
        taper = hook << gf.components.taper(length=0.4, width1=0.05, width2=0.01, cross_section=xs)
        taper.connect("o1", straight.ports["o2"])
        
        if mirror:
            hook.mirror()
            
        return hook

    # Add Top Hook
    top_hook = c << create_hook(mirror=False)
    top_hook.move((0, 0.4))
    
    # Add Bottom Hook
    bottom_hook = c << create_hook(mirror=True)
    bottom_hook.move((length, -0.4))
    
    return c

if __name__ == "__main__":
    device = device_geometry()
    device.write_gds("device_recreated.gds")
    print("GDS file created successfully with custom radius.")