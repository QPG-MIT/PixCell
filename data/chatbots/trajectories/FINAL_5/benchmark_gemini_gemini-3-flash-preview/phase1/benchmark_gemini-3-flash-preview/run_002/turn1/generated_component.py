import gdsfactory as gf

@gf.cell
def recreated_device():
    c = gf.Component("recreated_device")
    
    # 1. Define strict dimensions to meet the 18.24 x 0.7 um footprint
    L_TOTAL = 18.24
    H_TOTAL = 0.7
    
    # Waveguide parameters
    wg_w = 0.04
    bb_w = 0.03
    gap = 0.06
    radius = 0.12
    
    # Section lengths
    backbone_len = L_TOTAL - 0.5
    taper_len = 3.5
    grating_len = 8.0
    # The top straight needs to connect the taper to the start of the 180 bend
    # The bend's "o1" is at the start of the arc.
    straight_top_len = (L_TOTAL / 2) + 1.0 - taper_len
    
    # Create CrossSections for layers (as per catalog section 3/4)
    xs_wg = gf.cross_section.cross_section(width=wg_w, layer=(1, 0))
    xs_bb = gf.cross_section.cross_section(width=bb_w, layer=(1, 0))

    # 2. Add Central Backbone (Catalog: gf.components.straight)
    backbone = c << gf.components.straight(length=backbone_len, cross_section=xs_bb)
    # Move manually instead of accessing .length on the reference
    backbone.movex(-backbone_len / 2)

    # 3. Define the asymmetric unit (one half of the device)
    def create_unit():
        u = gf.Component()
        
        # A. Taper (Catalog: length, width1, width2)
        # Note: If taper doesn't support cross_section directly, we use layer (typical GDSFactory)
        taper = u << gf.components.taper(length=taper_len, width1=0.001, width2=wg_w)
        
        # B. Top Straight
        s_top = u << gf.components.straight(length=straight_top_len, cross_section=xs_wg)
        s_top.connect("o1", taper.ports["o2"])
        
        # C. 180-degree Bend (Catalog: radius, angle, cross_section)
        bend = u << gf.components.bend_circular(radius=radius, angle=180, cross_section=xs_wg)
        bend.connect("o1", s_top.ports["o2"])
        
        # D. Grating Base
        grating_base = u << gf.components.straight(length=grating_len, cross_section=xs_wg)
        grating_base.connect("o1", bend.ports["o2"])
        
        # Periodic Grating Teeth (Catalog: rectangle, add_array)
        tooth_w = 0.04
        tooth_h = wg_w * 3
        tooth = gf.components.rectangle(size=(tooth_w, tooth_h), layer=(1, 0), centered=True)
        num_teeth = 40
        # Use add_array from Key Assembly Operations table
        teeth = u.add_array(tooth, columns=num_teeth, rows=1, spacing=(grating_len/num_teeth, 0))
        # Position teeth over the grating base
        teeth.move(grating_base.center)
        
        # E. Outward S-Bend (Catalog: size, cross_section)
        # Size is (dx, dy). dx extends to roughly the end of the footprint
        flare_dx = L_TOTAL - (straight_top_len + taper_len + radius)
        flare = u << gf.components.bend_s(size=(flare_dx, 0.12), cross_section=xs_wg)
        flare.mirror()
        flare.connect("o1", grating_base.ports["o2"])
        
        return u

    # 4. Instantiate and position Units
    # Top Unit
    unit_top = c << create_unit()
    y_shift = (bb_w / 2) + gap + radius
    unit_top.movey(y_shift)
    unit_top.movex(-L_TOTAL/2 + 0.1) # Align taper to left edge

    # Bottom Unit (180 deg rotation)
    unit_bot = c << create_unit()
    unit_bot.rotate(180)
    unit_bot.movey(-y_shift)
    unit_bot.movex(L_TOTAL/2 - 0.1) # Align taper to right edge

    return c

if __name__ == "__main__":
    device = recreated_device()
    
    # Calculate footprint to verify constraint
    # We use get_bounding_box() instead of .bbox for better compatibility
    bbox = device.get_bounding_box()
    width = bbox[1][0] - bbox[0][0]
    height = bbox[1][1] - bbox[0][1]
    
    print(f"Final Footprint: {width:.2f} x {height:.2f} um")
    # device.show()