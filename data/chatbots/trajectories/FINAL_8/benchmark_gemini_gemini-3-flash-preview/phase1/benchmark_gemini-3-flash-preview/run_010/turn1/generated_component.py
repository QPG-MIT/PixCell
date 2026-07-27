import gdsfactory as gf

@gf.cell
def recreate_image_device():
    """
    Recreates the device from the provided image using parametric 
    primitives and assembly patterns from GDSFactory.
    """
    c = gf.Component("device_reconstruction")
    layer = (1, 0)

    # 1. PARAMETRIC CROSS-SECTION DEFINITIONS
    # Define the 5 central horizontal lines
    xs_center = gf.cross_section.cross_section(
        sections=[
            gf.Section(width=0.1, offset=y, layer=layer) 
            for y in [-0.3, -0.15, 0, 0.15, 0.3]
        ]
    )
    
    # Define the side blocks: 1 thick base (0.4um) and 5 thinner lines (0.06um)
    xs_block = gf.cross_section.cross_section(
        sections=[
            gf.Section(width=0.4, offset=0, layer=layer),
            gf.Section(width=0.06, offset=0.3, layer=layer),
            gf.Section(width=0.06, offset=0.42, layer=layer),
            gf.Section(width=0.06, offset=0.54, layer=layer),
            gf.Section(width=0.06, offset=0.66, layer=layer),
            gf.Section(width=0.06, offset=0.78, layer=layer),
        ]
    )

    # 2. BUILDING THE CENTRAL SECTION
    # Straight waveguides running through the middle (120um length)
    center_wg = c << gf.components.straight(length=120, cross_section=xs_center)
    center_wg.movex(-60) # Center at origin

    # 3. BUILDING THE TOP FLARING BLOCK
    # We assemble this from a straight center and two curved ends (Euler bends)
    block_comp = gf.Component("flaring_block")
    
    # Straight middle segment of the block
    mid = block_comp << gf.components.straight(length=70, cross_section=xs_block)
    mid.movex(-35)
    
    # Right flare (Euler bend for smooth adiabatic transition)
    flare_r = block_comp << gf.components.bend_euler(radius=160, angle=5, cross_section=xs_block)
    flare_r.connect("o1", mid.ports["o2"])
    
    # Left flare (Mirroring the right flare)
    flare_l = block_comp << gf.components.bend_euler(radius=160, angle=5, cross_section=xs_block)
    flare_l.mirror((0, 1)) # Mirror across Y axis to face left
    flare_l.connect("o1", mid.ports["o1"])
    
    # 4. FINAL ASSEMBLY
    # Add top block
    top_inst = c << block_comp
    top_inst.movey(0.7)
    
    # Add bottom block by mirroring the top block across the horizontal axis
    bottom_inst = c << block_comp
    bottom_inst.mirror((1, 0)) # Mirror across X axis
    bottom_inst.movey(-0.7)

    return c

if __name__ == "__main__":
    # Create the component
    device = recreate_image_device()
    
    # Define the output filename
    gds_filename = "recreated_device_geometry.gds"
    
    # EXPLICITLY WRITE THE GDS FILE
    device.write_gds(gds_filename)
    
    print(f"Success: GDS file '{gds_filename}' has been generated.")
    # device.show() # Uncomment to view in KLayout if installed