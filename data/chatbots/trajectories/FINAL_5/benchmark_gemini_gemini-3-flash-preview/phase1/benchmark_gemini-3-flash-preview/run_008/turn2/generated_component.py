import gdsfactory as gf

@gf.cell
def recreate_device():
    """
    Recreates the device geometry with corrected DBU-compliant widths.
    Footprint: 18.24um x 0.7um.
    """
    c = gf.Component("device_recreation")
    
    # PARAMETERS (Using even nm values to satisfy DBU constraints)
    # 0.044um = 44nm (divisible by 2)
    # 0.002um = 2nm (divisible by 2)
    wg_width = 0.044 
    layer = (1, 0)
    
    # Cross-section with small radius allowance
    xs = gf.cross_section.cross_section(
        width=wg_width, 
        layer=layer, 
        radius_min=0.01
    )

    # 1. Central Bus Waveguide
    # Spans the middle of the device
    bus = c << gf.components.straight(length=18.24, cross_section=xs)
    bus.movex(-18.24 / 2)

    # 2. Define the 'Arm' sub-component
    def create_arm():
        arm = gf.Component()
        
        # Backbone: The segment parallel to the bus that hosts the grating
        backbone_l = 8.5
        backbone = arm << gf.components.straight(length=backbone_l, cross_section=xs)
        
        # Grating: Vertical teeth along the backbone
        # tooth_w = 0.032um = 32nm (even)
        num_teeth = 60
        tooth_w = 0.032
        tooth_h = 0.22
        period = backbone_l / num_teeth
        for i in range(num_teeth):
            rect = arm << gf.components.rectangle(size=(tooth_w, tooth_h), layer=layer, centered=True)
            rect.x = i * period + tooth_w/2
            
        # HAIRPIN (Right Side)
        # Use bend_circular for small radii to avoid Euler spiral artifacts at this scale
        u_turn = arm << gf.components.bend_circular(radius=0.14, angle=180, cross_section=xs)
        u_turn.connect("o1", backbone.ports["o2"])
        
        # NEEDLE (Top of the Hairpin)
        # Long taper pointing back towards the left
        needle = arm << gf.components.taper(
            length=13.0, 
            width1=wg_width, 
            width2=0.002, 
            layer=layer
        )
        needle.connect("o1", u_turn.ports["o2"])
        
        # TAIL (Left Side)
        # Gentle curve and taper sweeping away
        tail_bend = arm << gf.components.bend_euler(radius=1.2, angle=-35, cross_section=xs)
        tail_bend.connect("o1", backbone.ports["o1"])
        
        tail_taper = arm << gf.components.taper(
            length=4.5, 
            width1=wg_width, 
            width2=0.002, 
            layer=layer
        )
        tail_taper.connect("o1", tail_bend.ports["o2"])
        
        return arm

    # 3. Assembly
    top_arm = c << create_arm()
    bot_arm = c << create_arm()
    
    # Centrosymmetric rotation
    bot_arm.rotate(180)
    
    # Final positioning
    # The gap between bus and backbone is small (~100nm)
    # Total height approx: 0.22 (teeth) + gap + bus + gap + 0.22 (teeth)
    top_arm.movey(0.12)
    bot_arm.movey(-0.12)
    
    # Horizontal shift to center the needles/tails within the footprint
    top_arm.movex(-2.5)
    bot_arm.movex(2.5)

    return c

if __name__ == "__main__":
    device = recreate_device()
    device.write_gds("final_device.gds")
    device.show()