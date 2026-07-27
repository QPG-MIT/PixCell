import gdsfactory as gf

@gf.cell
def racetrack_mzi():
    """
    Creates a racetrack ring resonator integrated with an internal Mach-Zehnder 
    Interferometer (MZI) structure.
    """
    layer = (1, 0)
    
    # 1. Outer Stadium Boundary
    # Footprint constraint is [3.0, 5.5] (height 3.0, width 5.5)
    # This corresponds to a central rectangle of dx=2.5, dy=3.0 and two semicircles of R=1.5
    c_outer = gf.Component("outer")
    c_outer.add_ref(gf.components.rectangle(size=(2.5, 3.0), centered=True, layer=layer))
    c_outer.add_ref(gf.components.circle(radius=1.5, layer=layer)).movex(-1.25)
    c_outer.add_ref(gf.components.circle(radius=1.5, layer=layer)).movex(1.25)
    
    # 2. Inner Stadium Boundary
    # Assuming a track thickness of 0.5, the inner height is 2.0 and inner radius is 1.0.
    c_inner = gf.Component("inner")
    c_inner.add_ref(gf.components.rectangle(size=(2.5, 2.0), centered=True, layer=layer))
    c_inner.add_ref(gf.components.circle(radius=1.0, layer=layer)).movex(-1.25)
    c_inner.add_ref(gf.components.circle(radius=1.0, layer=layer)).movex(1.25)
    
    # 3. Create the Main Track (Outer minus Inner)
    track = gf.boolean(c_outer, c_inner, operation="not", layer=layer)
    
    # 4. MZI Solid Arms Construction
    # We build the split arms via parameterized paths.
    # The trunks start slightly inside the track wall (x=+/-2.35) to ensure a perfectly clean boolean union later.
    xs = gf.cross_section.cross_section(width=0.5, layer=layer)
    
    # Upper branch path
    p_up = gf.Path([(-2.35, 0), (-1.25, 0), (-0.8, 0.45), (0.8, 0.45), (1.25, 0), (2.35, 0)])
    c_up = gf.path.extrude(p_up, cross_section=xs)
    
    # Lower branch path
    p_dn = gf.Path([(-2.35, 0), (-1.25, 0), (-0.8, -0.45), (0.8, -0.45), (1.25, 0), (2.35, 0)])
    c_dn = gf.path.extrude(p_dn, cross_section=xs)
    
    # Union of paths creates the solid MZI shape (including exact sharp > Y-branch inner wedges)
    mzi_solid = gf.boolean(c_up, c_dn, operation="or", layer=layer)
    
    # 5. Hollow Cutouts (Rectangular "ladder" holes)
    # Holes are positioned leaving a uniform 0.1 border inside the 0.5-thick boxes
    # Top box Y-center is 0.45, bottom box Y-center is -0.45.
    c_holes = gf.Component("holes")
    hole_rect = gf.components.rectangle(size=(0.6, 0.3), centered=True, layer=layer)
    
    # Top arm holes
    c_holes.add_ref(hole_rect).move((-0.4, 0.45))
    c_holes.add_ref(hole_rect).move((0.4, 0.45))
    
    # Bottom arm holes
    c_holes.add_ref(hole_rect).move((-0.4, -0.45))
    c_holes.add_ref(hole_rect).move((0.4, -0.45))
    
    # 6. Subtract holes to finalize the internal MZI
    mzi_hollow = gf.boolean(mzi_solid, c_holes, operation="not", layer=layer)
    
    # 7. Final Assembly
    # Merge the outer ring track with the fully detailed MZI
    final_device = gf.boolean(track, mzi_hollow, operation="or", layer=layer)
    
    return final_device

if __name__ == "__main__":
    # Standard generation block: builds the device and exports it safely
    c = racetrack_mzi()
    c.write_gds("racetrack_mzi.gds")