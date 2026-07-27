import gdsfactory as gf

@gf.cell
def custom_mzi_resonator():
    """
    Creates a custom geometry featuring an outer racetrack ring 
    and an internal split Mach-Zehnder style structure with hollow blocks.
    Designed to fit exactly in a 5.5 x 3.0 um footprint.
    """
    layer = (1, 0)

    # --- 1. Racetrack Ring ---
    # Build outer solid shape safely by translating references
    c_outer = gf.Component("outer_solid")
    c_outer << gf.components.rectangle(size=(2.5, 3.0), centered=True, layer=layer)
    ref_cl = c_outer << gf.components.circle(radius=1.5, layer=layer)
    ref_cl.movex(-1.25)
    ref_cr = c_outer << gf.components.circle(radius=1.5, layer=layer)
    ref_cr.movex(1.25)

    # Build inner void for subtraction
    c_inner = gf.Component("inner_void")
    c_inner << gf.components.rectangle(size=(2.5, 2.2), centered=True, layer=layer)
    ref_icl = c_inner << gf.components.circle(radius=1.1, layer=layer)
    ref_icl.movex(-1.25)
    ref_icr = c_inner << gf.components.circle(radius=1.1, layer=layer)
    ref_icr.movex(1.25)

    # Boolean difference to create the hollow ring (layer explicitly passed)
    ring = gf.boolean(c_outer, c_inner, operation='not', layer=layer)

    # --- 2. Inner Split Arms (MZI Structure) ---
    # Paths for the thin arms and the merged trunk.
    # Offsetting the paths vertically by +/- 0.1 makes them overlap at the trunk 
    # to form a wider trunk total width of 0.4, while individual arms are 0.2 wide.
    p_up = gf.Path([(-2.4, 0.1), (-1.5, 0.1), (-0.7, 0.45), (0.7, 0.45), (1.5, 0.1), (2.4, 0.1)])
    p_dn = gf.Path([(-2.4, -0.1), (-1.5, -0.1), (-0.7, -0.45), (0.7, -0.45), (1.5, -0.1), (2.4, -0.1)])
    
    xs = gf.cross_section.cross_section(width=0.2, layer=layer)
    arm_up = gf.path.extrude(p_up, cross_section=xs)
    arm_dn = gf.path.extrude(p_dn, cross_section=xs)
    
    c_arms = gf.Component("arms")
    c_arms << arm_up
    c_arms << arm_dn

    # --- 3. Thick Rectangular Blocks ---
    c_blocks = gf.Component("blocks")
    ref_b1 = c_blocks << gf.components.rectangle(size=(1.4, 0.4), centered=True, layer=layer)
    ref_b1.move((0, 0.45))
    ref_b2 = c_blocks << gf.components.rectangle(size=(1.4, 0.4), centered=True, layer=layer)
    ref_b2.move((0, -0.45))

    # Assemble arms and blocks into one component for boolean ops
    c_arms_blocks = gf.Component("arms_blocks")
    c_arms_blocks << c_arms
    c_arms_blocks << c_blocks

    # Union the arms and blocks to create a single solid continuous shape
    arms_solid = gf.boolean(c_arms, c_blocks, operation='or', layer=layer)

    # --- 4. Rectangular Voids in Blocks ---
    c_holes = gf.Component("holes")
    
    # Helper to securely add and translate a hole reference
    def add_hole(parent, center):
        ref = parent << gf.components.rectangle(size=(0.4, 0.2), centered=True, layer=layer)
        ref.move(center)

    # Add 4 holes in total, positioned symmetrically in the thick blocks
    add_hole(c_holes, (-0.3, 0.45))  # Top Left
    add_hole(c_holes, (0.3, 0.45))   # Top Right
    add_hole(c_holes, (-0.3, -0.45)) # Bottom Left
    add_hole(c_holes, (0.3, -0.45))  # Bottom Right

    # Subtract holes to hollow out the rectangular blocks
    inner_mzi = gf.boolean(arms_solid, c_holes, operation='not', layer=layer)

    # --- 5. Final Assembly ---
    # Union the outer ring with the intricate inner structure
    final_shape = gf.boolean(ring, inner_mzi, operation='or', layer=layer)

    # Pack into the final device wrapper
    c = gf.Component("final_custom_device")
    c << final_shape

    return c


if __name__ == "__main__":
    c = custom_mzi_resonator()
    c.show()