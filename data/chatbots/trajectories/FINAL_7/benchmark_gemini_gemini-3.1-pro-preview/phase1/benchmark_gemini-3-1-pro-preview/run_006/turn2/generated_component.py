import gdsfactory as gf

@gf.cell
def slotted_block() -> gf.Component:
    """Creates a rectangular block with two rectangular cutouts."""
    c = gf.Component("slotted_block")
    
    # Outer solid box
    outer = gf.components.rectangle(size=(1.8, 0.6), centered=True, layer=(1, 0))
    
    # Two rectangular holes to subtract
    holes = gf.Component("holes")
    h1 = holes << gf.components.rectangle(size=(0.7, 0.3), centered=True, layer=(1, 0))
    h1.movex(-0.45)
    h2 = holes << gf.components.rectangle(size=(0.7, 0.3), centered=True, layer=(1, 0))
    h2.movex(0.45)
    
    # Perform Boolean NOT
    return gf.boolean(outer, holes, operation="not", layer=(1, 0))


@gf.cell
def racetrack_mzi_device() -> gf.Component:
    """
    Creates the symmetric racetrack MZI device matching the 5.5 x 3.0 footprint.
    """
    c = gf.Component("racetrack_mzi_device")
    
    # ----------------------------------------------------
    # 1. Outer Racetrack Frame
    # ----------------------------------------------------
    # For a 5.5 x 3.0 footprint and 0.4 track width:
    # Path Radius = (3.0 - 0.4) / 2 = 1.3
    # Straight length = 5.5 - (2 * 1.3) - 0.4 = 2.5
    p_ring = gf.Path()
    p_ring.append(gf.path.straight(length=2.5))
    p_ring.append(gf.path.arc(radius=1.3, angle=-180))
    p_ring.append(gf.path.straight(length=2.5))
    p_ring.append(gf.path.arc(radius=1.3, angle=-180))
    
    ring_xs = gf.cross_section.cross_section(width=0.4, layer=(1, 0))
    ring_ext = gf.path.extrude(p_ring, cross_section=ring_xs)
    
    ring_centered = gf.Component("ring_centered")
    r_ref = ring_centered << ring_ext
    r_ref.move((-1.25, 1.3))  # Center natively on origin
    
    # ----------------------------------------------------
    # 2. Inner MZI Structure
    # ----------------------------------------------------
    inner = gf.Component("inner_mzi")
    
    # Left and Right central stems (Connecting edge of inner ring to splits)
    # The inner left edge of the ring is at x = -2.35. The splits start at x = -1.25.
    stem_l = inner << gf.components.rectangle(size=(1.1, 0.35), centered=True, layer=(1, 0))
    stem_l.move((-1.8, 0))
    
    stem_r = inner << gf.components.rectangle(size=(1.1, 0.35), centered=True, layer=(1, 0))
    stem_r.move((1.8, 0))
    
    # Angled splitter arms
    xs_arm = gf.cross_section.cross_section(width=0.2, layer=(1, 0))
    
    p_up = gf.Path([(-1.4, 0), (-0.9, 0.45), (0.9, 0.45), (1.4, 0)])
    inner << gf.path.extrude(p_up, cross_section=xs_arm)
    
    p_dn = gf.Path([(-1.4, 0), (-0.9, -0.45), (0.9, -0.45), (1.4, 0)])
    inner << gf.path.extrude(p_dn, cross_section=xs_arm)
    
    # Add the slotted functional blocks to the straight portions of the arms
    block_ref_up = inner << slotted_block()
    block_ref_up.move((0, 0.45))
    
    block_ref_dn = inner << slotted_block()
    block_ref_dn.move((0, -0.45))
    
    # ----------------------------------------------------
    # 3. Final Union
    # ----------------------------------------------------
    # Boolean OR merges everything securely into a single contiguous polygon.
    # Hierarchical components are handled automatically without needing explicit flattening.
    final_device = gf.boolean(ring_centered, inner, operation="or", layer=(1, 0))
    
    c << final_device
    return c


if __name__ == "__main__":
    # Generate the component and write directly to GDS file
    c = racetrack_mzi_device()
    c.write_gds("racetrack_mzi_device.gds")