import gdsfactory as gf

@gf.cell
def recreated_device_silhouette():
    """
    Recreates the device silhouette with correct visual proportions.
    Total Height: 25um (4um bottom + 14um body + 7um top pins)
    Total Width: 10um
    """
    layer = (1, 0)
    
    # 1. MAIN BODY
    # A central rectangle. We make it 14um tall to leave room for large pins.
    body_w = 10.0
    body_h = 14.0
    body = gf.components.rectangle(size=(body_w, body_h), layer=layer, centered=True)
    
    # 2. TOP PINS ASSEMBLY
    # Each pin consists of a tapered base and a straight neck.
    # Total pin height: 7um (3um taper + 4um straight)
    tp_taper_h = 3.0
    tp_straight_h = 4.0
    tp_base_w = 1.8   # Substantial width to match visual
    tp_tip_w = 0.8
    
    # Construct a single pin sub-assembly
    pin_part = gf.Component("single_top_pin")
    tap = pin_part << gf.components.taper(
        length=tp_taper_h, width1=tp_base_w, width2=tp_tip_w, layer=layer
    )
    # Define a cross-section for the straight part
    xs_tip = gf.cross_section.cross_section(width=tp_tip_w, layer=layer)
    strt = pin_part << gf.components.straight(length=tp_straight_h, cross_section=xs_tip)
    
    # Align the straight tip to the end of the taper
    strt.connect("o1", tap.ports["o2"])
    
    # Component to hold all protrusions for a single merge operation
    protrusions = gf.Component("protrusions")
    
    # Place 4 pins along the top edge of the body (y = 7)
    # Spaced clearly across the 10um width
    x_offsets = [-3.6, -1.2, 1.2, 3.6]
    for x in x_offsets:
        p = protrusions << pin_part
        p.rotate(90)
        p.move((x, body_h / 2))
        
    # 3. BOTTOM PIN
    # A single, larger tapered protrusion at the center bottom.
    # Height: 4um
    bp_h = 4.0
    bp_w1 = 3.0
    bp_w2 = 1.2
    btap = protrusions << gf.components.taper(
        length=bp_h, width1=bp_w1, width2=bp_w2, layer=layer
    )
    btap.rotate(-90)
    btap.move((0, -body_h / 2))
    
    # 4. FINAL MERGE (BOOLEAN OR)
    # Combine the body and all pins into one continuous solid silhouette.
    # Total Y height = 4 (bottom) + 14 (body) + 7 (top) = 25.0 um
    # Total X width = 10.0 um
    final_device = gf.boolean(A=body, B=protrusions, operation="or", layer=layer)
    final_device.name = "device_recreation"
    
    return final_device

if __name__ == "__main__":
    # Create the component
    c = recreated_device_silhouette()
    
    # Write to GDS file
    filename = "recreated_device_v2.gds"
    c.write_gds(filename)
    
    print(f"Success: '{filename}' created.")
    print(f"Verified Width: {c.xsize} um")
    print(f"Verified Height: {c.ysize} um")