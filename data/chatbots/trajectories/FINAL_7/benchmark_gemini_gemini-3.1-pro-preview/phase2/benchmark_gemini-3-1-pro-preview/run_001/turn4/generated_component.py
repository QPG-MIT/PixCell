import gdsfactory as gf

@gf.cell
def device():
    """Assembles the stadium-shaped Mach-Zehnder Interferometer (MZI)."""
    layer = (1, 0)
    
    # --- 1. Construct the Outer Stadium Track ---
    # Create the outer solid shape (rectangle + 2 semi-circles)
    c_track_out = gf.Component("track_outer")
    c_track_out << gf.components.rectangle(size=(2.5, 3.0), centered=True, layer=layer)
    ref_out_l = c_track_out << gf.components.circle(radius=1.5, layer=layer)
    ref_out_l.movex(-1.25)
    ref_out_r = c_track_out << gf.components.circle(radius=1.5, layer=layer)
    ref_out_r.movex(1.25)
    
    # Create the inner cutout shape
    c_track_in = gf.Component("track_inner")
    c_track_in << gf.components.rectangle(size=(2.5, 2.0), centered=True, layer=layer)
    ref_in_l = c_track_in << gf.components.circle(radius=1.0, layer=layer)
    ref_in_l.movex(-1.25)
    ref_in_r = c_track_in << gf.components.circle(radius=1.0, layer=layer)
    ref_in_r.movex(1.25)
    
    # Subtract inner from outer to get the 0.5um thick continuous track loop
    track = gf.boolean(c_track_out, c_track_in, operation='not', layer=layer)
    
    # --- 2. Construct the Solid Inner MZI Components ---
    c_solid = gf.Component("inner_solid")
    
    # Extrude the routing arms (Width = 0.2)
    # The horizontal path segments from x=-2.5 to x=-1.6 perfectly overlap at y=0
    # to naturally form the thicker 0.4um horizontal stem without any gaps or notches.
    xs = gf.cross_section.cross_section(width=0.2, layer=layer)
    
    p_top = gf.Path([
        (-2.5, 0.1),     # Starts deep inside track wall to ensure clean merge
        (-1.6, 0.1),     # End of merged horizontal stem
        (-1.2, 0.5),     # Angled branch up
        (1.2, 0.5),      # Horizontal straight across
        (1.6, 0.1),      # Angled branch down
        (2.5, 0.1)       # End deep inside opposite track wall
    ])
    c_solid << gf.path.extrude(p_top, cross_section=xs)
    
    p_bot = gf.Path([
        (-2.5, -0.1),
        (-1.6, -0.1),
        (-1.2, -0.5),
        (1.2, -0.5),
        (1.6, -0.1),
        (2.5, -0.1)
    ])
    c_solid << gf.path.extrude(p_bot, cross_section=xs)
    
    # Layer the thicker solid blocks over the central straight sections of the arms
    # The blocks are 1.8um long, leaving 0.3um of thin straight arm exposed on each side.
    ref_block_t = c_solid << gf.components.rectangle(size=(1.8, 0.4), centered=True, layer=layer)
    ref_block_t.movey(0.5)
    ref_block_b = c_solid << gf.components.rectangle(size=(1.8, 0.4), centered=True, layer=layer)
    ref_block_b.movey(-0.5)
    
    # --- 3. Define the Rectangular Cutouts (Holes) ---
    c_holes = gf.Component("inner_holes")
    hole_size = (0.6, 0.2)
    
    # Top block holes (spaced leaving 0.2um walls on ends and middle)
    ref_h1 = c_holes << gf.components.rectangle(size=hole_size, centered=True, layer=layer)
    ref_h1.move((-0.4, 0.5))
    ref_h2 = c_holes << gf.components.rectangle(size=hole_size, centered=True, layer=layer)
    ref_h2.move((0.4, 0.5))
    
    # Bottom block holes
    ref_h3 = c_holes << gf.components.rectangle(size=hole_size, centered=True, layer=layer)
    ref_h3.move((-0.4, -0.5))
    ref_h4 = c_holes << gf.components.rectangle(size=hole_size, centered=True, layer=layer)
    ref_h4.move((0.4, -0.5))
    
    # --- 4. Subtraction & Final Assembly ---
    # Subtract the holes from the merged arms/blocks to create the hollow inner geometry
    mzi_core = gf.boolean(c_solid, c_holes, operation='not', layer=layer)
    
    # Group into the final component
    final_device = gf.Component("MZI_stadium")
    final_device << track
    final_device << mzi_core
    
    return final_device

if __name__ == "__main__":
    c = device()
    c.write_gds("device.gds")