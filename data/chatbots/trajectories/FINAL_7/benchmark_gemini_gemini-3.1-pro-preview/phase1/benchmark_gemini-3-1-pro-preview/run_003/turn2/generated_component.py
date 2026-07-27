import gdsfactory as gf

@gf.cell
def racetrack_mzi():
    """
    Creates a racetrack ring resonator integrated with an internal Mach-Zehnder 
    Interferometer (MZI) structure.
    
    Uses pure Constructive Solid Geometry (CSG) to completely eliminate 
    path extrusion miter artifacts and zero-width validation errors.
    """
    layer = (1, 0)

    # ==========================================================
    # 1. Main Track (Stadium Shape)
    # Footprint constraint [3.0, 5.5] is strictly respected.
    # Total width = 2.5 + 2*(1.5) = 5.5. Total height = 3.0.
    # ==========================================================
    c_outer = gf.Component("outer")
    c_outer.add_ref(gf.components.rectangle(size=(2.5, 3.0), centered=True, layer=layer))
    c_outer.add_ref(gf.components.circle(radius=1.5, layer=layer)).movex(-1.25)
    c_outer.add_ref(gf.components.circle(radius=1.5, layer=layer)).movex(1.25)

    c_inner = gf.Component("inner")
    c_inner.add_ref(gf.components.rectangle(size=(2.5, 2.0), centered=True, layer=layer))
    c_inner.add_ref(gf.components.circle(radius=1.0, layer=layer)).movex(-1.25)
    c_inner.add_ref(gf.components.circle(radius=1.0, layer=layer)).movex(1.25)

    track = gf.boolean(c_outer, c_inner, operation="not", layer=layer)

    # ==========================================================
    # 2. Inner MZI Solid Base
    # Build a solid spindle shape that we will hollow out.
    # Tapers are used to perfectly form the outer angled boundaries.
    # ==========================================================
    c_mzi_solid = gf.Component("mzi_solid")
    
    # Central thick block covering both arm areas
    c_mzi_solid.add_ref(gf.components.rectangle(size=(1.6, 1.4), centered=True, layer=layer))
    
    # Left taper (expanding from stem to main block)
    taper_left = gf.components.taper(length=0.45, width1=0.4, width2=1.4, layer=layer)
    c_mzi_solid.add_ref(taper_left).movex(-1.025)
    
    # Right taper (contracting from main block to stem)
    taper_right = gf.components.taper(length=0.45, width1=1.4, width2=0.4, layer=layer)
    c_mzi_solid.add_ref(taper_right).movex(1.025)
    
    # Connecting stems (reach slightly inside the track inner wall for clean boolean union)
    stem_left = gf.components.rectangle(size=(1.05, 0.4), centered=True, layer=layer)
    c_mzi_solid.add_ref(stem_left).movex(-1.775) 
    
    stem_right = gf.components.rectangle(size=(1.05, 0.4), centered=True, layer=layer)
    c_mzi_solid.add_ref(stem_right).movex(1.775) 

    # ==========================================================
    # 3. Inner MZI Subtractions (Holes & Splits)
    # Shapes representing empty space to be subtracted from the solid base.
    # ==========================================================
    c_mzi_holes = gf.Component("mzi_holes")
    
    # Central horizontal gap separating the upper and lower main arms
    c_mzi_holes.add_ref(gf.components.rectangle(size=(1.6, 0.4), centered=True, layer=layer))
    
    # Left inner wedge to hollow out the Y-split
    # Note: Using 0.002 instead of 0.0 prevents the Pydantic ValidationError while 
    # functionally acting as a perfectly sharp visual point (2 nanometers wide).
    wedge_left = gf.components.taper(length=0.45, width1=0.002, width2=0.4, layer=layer)
    c_mzi_holes.add_ref(wedge_left).movex(-1.025)
    
    # Right inner wedge to hollow out the Y-combine
    wedge_right = gf.components.taper(length=0.45, width1=0.4, width2=0.002, layer=layer)
    c_mzi_holes.add_ref(wedge_right).movex(1.025)
    
    # Rectangular cutouts in the horizontal arms
    hole_rect = gf.components.rectangle(size=(0.575, 0.2), centered=True, layer=layer)
    
    # Upper arm cutouts
    c_mzi_holes.add_ref(hole_rect).move((-0.3625, 0.45))
    c_mzi_holes.add_ref(hole_rect).move((0.3625, 0.45))
    
    # Lower arm cutouts
    c_mzi_holes.add_ref(hole_rect).move((-0.3625, -0.45))
    c_mzi_holes.add_ref(hole_rect).move((0.3625, -0.45))

    # ==========================================================
    # 4. Final Boolean Assembly
    # ==========================================================
    
    # Subtract the holes from the solid MZI block to form the final MZI shape
    mzi_final = gf.boolean(c_mzi_solid, c_mzi_holes, operation="not", layer=layer)
    
    # Merge the outer ring track with the fully detailed MZI
    final_device = gf.boolean(track, mzi_final, operation="or", layer=layer)

    return final_device

if __name__ == "__main__":
    c = racetrack_mzi()
    c.write_gds("racetrack_mzi.gds")