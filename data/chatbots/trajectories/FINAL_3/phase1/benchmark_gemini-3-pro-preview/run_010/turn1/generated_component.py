import gdsfactory as gf

@gf.cell
def directional_coupler_4x240():
    """
    Creates a directional coupler matching the visual and footprint constraints
    using only catalog primitives.
    
    Footprint: 4 um x 240 um
    """
    c = gf.Component("Directional_Coupler_4x240")
    
    # --- 1. Define Parameters based on constraints ---
    length_total = 240.0
    height_total = 4.0
    
    wg_width = 0.5
    gap = 0.2
    
    # Calculate lengths
    # Visual estimation: Coupling region is roughly 1/4 of total length (60um)
    # Remaining 180um is split between two bends (90um each)
    length_coupling = 60.0 
    length_bend = (length_total - length_coupling) / 2 
    
    # Calculate vertical shift (dy) for S-bends
    # Inner center y (coupling) = +/- (gap/2 + width/2) = +/- 0.35
    # Outer center y (ports) = +/- (height_total/2 - width/2) = +/- 1.75
    # Shift per arm = 1.75 - 0.35 = 1.4 um
    dy = 1.4
    
    # Define Cross Section
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))

    # --- 2. Instantiate Primitives ---
    
    # A. Central Straight Coupler
    # Catalog Function: gf.components.coupler_straight
    # Ports: o1 (west top), o2 (west bottom), o3 (east bottom), o4 (east top)
    core = c << gf.components.coupler_straight(
        length=length_coupling, 
        gap=gap, 
        cross_section=xs
    )
    
    # B. Define the S-Bend Geometry
    # Catalog Function: gf.components.bend_s
    # size=(x, y) creates a bend from (0,0) to (x,y)
    bend_component = gf.components.bend_s(
        size=(length_bend, dy), 
        cross_section=xs
    )

    # --- 3. Assembly and Connections ---
    
    # -- Inputs (Left Side) --
    
    # Top Left Bend: Needs to go DOWN from input to coupler
    btl = c << bend_component
    btl.mirror_y() # Mirror to bend downwards
    # Connect the END of the bend ("o2") to the coupler input ("o1")
    btl.connect("o2", core.ports["o1"])
    
    # Bottom Left Bend: Needs to go UP from input to coupler
    bbl = c << bend_component
    # Standard bend_s goes up, so no mirror needed
    bbl.connect("o2", core.ports["o2"])
    
    # -- Outputs (Right Side) --
    
    # Top Right Bend: Needs to go UP from coupler to output
    btr = c << bend_component
    # Connect START of bend ("o1") to coupler output ("o4")
    btr.connect("o1", core.ports["o4"])
    
    # Bottom Right Bend: Needs to go DOWN from coupler to output
    bbr = c << bend_component
    bbr.mirror_y() # Mirror to bend downwards
    bbr.connect("o1", core.ports["o3"])
    
    # --- 4. Expose Ports ---
    c.add_port("o1", port=btl.ports["o1"]) # Input Top
    c.add_port("o2", port=bbl.ports["o1"]) # Input Bottom
    c.add_port("o3", port=bbr.ports["o2"]) # Output Bottom
    c.add_port("o4", port=btr.ports["o2"]) # Output Top
    
    return c

if __name__ == "__main__":
    # 1. Generate the device
    device = directional_coupler_4x240()
    
    # 2. Write to GDS file (Crucial Step)
    gds_filename = "directional_coupler_4x240.gds"
    device.write_gds(gds_filename)
    
    print(f"Success! GDS file created: {gds_filename}")
    print(f"Device Footprint: {device.size_info}")