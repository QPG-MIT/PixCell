import gdsfactory as gf

@gf.cell
def sine_taper(length, width1, width2, layer=(1, 0)):
    xs1 = gf.cross_section.cross_section(width=width1, layer=layer)
    xs2 = gf.cross_section.cross_section(width=width2, layer=layer)
    trans = gf.path.transition(xs1, xs2, width_type='sine')
    p = gf.path.straight(length=length)
    return gf.path.extrude_transition(p, trans)

@gf.cell
def bulb_arm(total_length=2.35, wide=2.4, l_fraction=0.3, layer=(1, 0)):
    narrow = 0.002  # Small positive even dbu value to avoid validation error
    l1 = total_length * l_fraction
    l2 = total_length - l1
    taper1 = sine_taper(l1, narrow, wide, layer)
    taper2 = sine_taper(l2, wide, narrow, layer)
    arm = gf.Component()
    t1 = arm << taper1
    t2 = arm << taper2
    t2.connect("o1", t1.ports["o2"])
    arm.add_port("o1", port=t1.ports["o1"])
    arm.add_port("o2", port=t2.ports["o2"])
    return arm

@gf.cell
def clover_device(layer=(1, 0)):
    c = gf.Component()
    arm = bulb_arm(layer=layer)
    
    angles = [0, 90, 180, 270]
    refs = []
    for angle in angles:
        ref = c << arm
        ref.rotate(angle, origin=(0, 0))
        refs.append(ref)
    
    # Pairwise boolean or to union them
    union1 = gf.boolean(refs[0], refs[1], operation="or", layer=layer)
    union2 = gf.boolean(refs[2], refs[3], operation="or", layer=layer)
    full_union = gf.boolean(union1, union2, operation="or", layer=layer)
    
    c << full_union
    return c

# Create the device
device = clover_device()
device.write_gds("clover_device.gds")