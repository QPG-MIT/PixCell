import gdsfactory as gf

@gf.cell
def tapered_coupler_device():
    c = gf.Component()

    # 1. Define Cross Sections for the widths
    # Narrow width for the tip and the start of the arms
    # Wide width for the base of the arms and the start of the center taper
    xs_narrow = gf.cross_section.cross_section(width=0.2, layer=(1, 0))
    xs_wide = gf.cross_section.cross_section(width=0.7, layer=(1, 0))

    # 2. Define Transition objects (Parametric width change)
    # Arms: Narrow -> Wide
    transition_out = gf.path.transition(xs_narrow, xs_wide, width_type="sine")
    # Center: Wide -> Narrow
    transition_in = gf.path.transition(xs_wide, xs_narrow, width_type="sine")

    # 3. Create the Geometry
    
    # Outer Arms (Top and Bottom)
    # Path length 40um (matches the total device footprint)
    p_outer = gf.path.straight(length=40)
    
    # Create top and bottom arms using extrude_transition
    arm_top = gf.path.extrude_transition(p_outer, transition_out)
    
    # Reference and position them (Offset Y by 0.5um to create the 1.0um gap)
    ref_top = c << arm_top
    ref_top.movey(0.5)
    
    ref_bot = c << arm_top
    ref_bot.movey(-0.5)

    # Middle Taper
    # Path length 20um (ends halfway)
    p_mid = gf.path.straight(length=20)
    
    # Extrude with inverse transition (Wide -> Narrow)
    mid_arm = gf.path.extrude_transition(p_mid, transition_in)
    ref_mid = c << mid_arm
    
    return c

# Create and verify the component
device = tapered_coupler_device()
device.write_gds("tapered_coupler.gds")