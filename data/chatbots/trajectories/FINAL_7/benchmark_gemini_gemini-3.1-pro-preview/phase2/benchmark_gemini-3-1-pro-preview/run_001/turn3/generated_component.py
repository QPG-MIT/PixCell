import gdsfactory as gf

@gf.cell
def device():
    """Assembles the stadium-shaped Mach-Zehnder Interferometer (MZI)."""
    layer = (1, 0)
    
    # --- 1. Construct the Outer Stadium Track ---
    c_track_out = gf.Component("track_outer")
    c_track_out << gf.components.rectangle(size=(2.5, 3.0), centered=True, layer=layer)
    # Move the reference, not the cached component
    ref_out_l = c_track_out << gf.components.circle(radius=1.5, layer=layer)
    ref_out_l.movex(-1.25)
    ref_out_r = c_track_out << gf.components.circle(radius=1.5, layer=layer)
    ref_out_r.movex(1.25)
    
    c_track_in = gf.Component("track_inner")
    c_track_in << gf.components.rectangle(size=(2.5, 2.0), centered=True, layer=layer)
    ref_in_l = c_track_in << gf.components.circle(radius=1.0, layer=layer)
    ref_in_l.movex(-1.25)
    ref_in_r = c_track_in << gf.components.circle(radius=1.0, layer=layer)
    ref_in_r.movex(1.25)
    
    # Subtract inner from outer to get the 0.5um thick track loop
    track = gf.boolean(c_track_out, c_track_in, operation='not', layer=layer)
    
    # --- 2. Construct the Solid Inner MZI Components ---
    c_solid = gf.Component("inner_solid")
    
    # Extrude the thinner routing arms (Width = 0.25)
    xs = gf.cross_section.cross_section(width=0.25, layer=layer)
    
    p_top = gf.Path([
        (-2.4, 0.125),   # Starts inside track wall, merges to form 0.5um stem
        (-1.8, 0.125),   # Horizontal stem section
        (-1.2, 0.4),     # Angled branch up
        (1.2, 0.4),      # Horizontal straight across the block
        (1.8, 0.125),    # Angled branch down
        (2.4, 0.125)     # End stem inside track wall
    ])
    c_solid << gf.path.extrude(p_top, cross_section=xs)
    
    p_bot = gf.Path([
        (-2.4, -0.125),  # Lower path naturally mirrors the upper
        (-1.8, -0.125),
        (-1.2, -0.4),
        (1.2, -0.4),
        (1.8, -0.125),
        (2.4, -0.125)
    ])
    c_solid << gf.path.extrude(p_bot, cross_section=xs)
    
    # Safety rects at the y=0 split to eliminate potential sub-nanometer boolean gaps
    ref_safe_l = c_solid << gf.components.rectangle(size=(0.7, 0.1), centered=True, layer=layer)
    ref_safe_l.movex(-2.05)
    ref_safe_r = c_solid << gf.components.rectangle(size=(0.7, 0.1), centered=True, layer=layer)
    ref_safe_r.movex(2.05)
    
    # Layer the thicker solid blocks over the arms (Width = 0.4)
    # The arms extending beyond x=1.0 create the "thin straight" step sections
    ref_block_t = c_solid << gf.components.rectangle(size=(2.0, 0.4), centered=True, layer=layer)
    ref_block_t.movey(0.4)
    ref_block_b = c_solid << gf.components.rectangle(size=(2.0, 0.4), centered=True, layer=layer)
    ref_block_b.movey(-0.4)
    
    # --- 3. Define the Rectangular Cutouts (Holes) ---
    c_holes = gf.Component("inner_holes")
    hole_size = (0.7, 0.2)
    
    # Top block holes
    ref_h1 = c_holes << gf.components.rectangle(size=hole_size, centered=True, layer=layer)
    ref_h1.move((-0.45, 0.4))
    ref_h2 = c_holes << gf.components.rectangle(size=hole_size, centered=True, layer=layer)
    ref_h2.move((0.45, 0.4))
    
    # Bottom block holes
    ref_h3 = c_holes << gf.components.rectangle(size=hole_size, centered=True, layer=layer)
    ref_h3.move((-0.45, -0.4))
    ref_h4 = c_holes << gf.components.rectangle(size=hole_size, centered=True, layer=layer)
    ref_h4.move((0.45, -0.4))
    
    # --- 4. Subtraction & Final Assembly ---
    # Subtract the holes from the merged arms/blocks to create the hollow shapes
    mzi_core = gf.boolean(c_solid, c_holes, operation='not', layer=layer)
    
    # Group into the final component
    final_device = gf.Component("MZI_stadium")
    final_device << track
    final_device << mzi_core
    
    return final_device

if __name__ == "__main__":
    c = device()
    c.write_gds("device.gds")