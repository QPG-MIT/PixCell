import gdsfactory as gf

@gf.cell
def recreated_device_v5():
    """
    Refined device silhouette with corrected aspect ratio.
    Target Footprint: 25um (Width) x 10um (Height)
    
    Proportions:
    - Bottom Pin: 1.0 um height
    - Main Body: 5.0 um height, 25.0 um width
    - Top Pins: 4.0 um height (1.5um taper + 2.5um straight)
    """
    layer = (1, 0)
    c = gf.Component("device_silhouette_v5")
    
    # --- 1. MAIN BODY ---
    # Centered at X=0, Y=3.5 (Bottom edge at Y=1.0, Top edge at Y=6.0)
    body_w = 25.0
    body_h = 5.0
    body = c << gf.components.rectangle(size=(body_w, body_h), layer=layer)
    body.movex(-body_w / 2)
    body.movey(1.0)
    
    # --- 2. TOP PINS ASSEMBLY ---
    tp_taper_h = 1.5
    tp_straight_h = 2.5
    tp_base_w = 1.6   # Flare at the body connection
    tp_tip_w = 0.6    # Thin neck width
    
    protrusions = gf.Component("protrusions")
    
    # Spacing pins across the top (X-offsets balanced for a 25um width)
    x_offsets = [-7.0, -2.4, 2.4, 7.0]
    
    for x in x_offsets:
        pin_part = gf.Component()
        
        # Tapered base element
        tap = pin_part << gf.components.taper(
            length=tp_taper_h, width1=tp_base_w, width2=tp_tip_w, layer=layer
        )
        
        # Thin straight neck
        xs_tip = gf.cross_section.cross_section(width=tp_tip_w, layer=layer)
        strt = pin_part << gf.components.straight(length=tp_straight_h, cross_section=xs_tip)
        strt.connect("o1", tap.ports["o2"])
        
        # Position the pin sitting on top of the body (Y=6.0)
        p_ref = protrusions << pin_part
        p_ref.rotate(90)
        p_ref.move((x, 6.0))

    # --- 3. BOTTOM PIN ---
    # Small tapered stub at the bottom center
    bp_h = 1.0
    bp_w1 = 2.0
    bp_w2 = 1.2
    btap = protrusions << gf.components.taper(
        length=bp_h, width1=bp_w1, width2=bp_w2, layer=layer
    )
    btap.rotate(-90)
    btap.move((0, 1.0)) # Starts at the bottom edge (Y=1.0) and goes down to Y=0

    # --- 4. FINAL ASSEMBLY ---
    # Merge all shapes into one continuous silhouette
    final_shape = gf.boolean(A=body, B=protrusions, operation="or", layer=layer)
    
    return final_shape

if __name__ == "__main__":
    # Create the component
    device = recreated_device_v5()
    
    # Export for visualization
    filename = "device_iteration_v5.gds"
    device.write_gds(filename)
    
    print(f"Success: '{filename}' generated.")
    print(f"Final Dimensions: {device.xsize:.2f}um wide x {device.ysize:.2f}um high")