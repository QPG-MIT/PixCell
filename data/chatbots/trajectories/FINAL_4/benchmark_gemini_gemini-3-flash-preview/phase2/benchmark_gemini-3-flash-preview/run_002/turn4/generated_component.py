import gdsfactory as gf

@gf.cell
def wavy_coupler_geometry():
    """
    Recreates the wavy waveguide coupler with perfect vertical and horizontal symmetry.
    Adjusted parameters to ensure a visible center gap and bold waveguide appearance.
    """
    c = gf.Component("wavy_coupler_v4")
    
    # 1. Dimensions based on the 18um x 3um footprint constraint
    total_width = 18.0
    total_height = 3.0
    
    # 2. Geometric tuning for visual match
    # Increasing width and providing a clear gap to prevent merging in the raster.
    wg_width = 0.8  
    center_gap = 0.3 
    
    # Calculate vertical offsets for the centerlines
    # y_center: vertical position of the waveguide centers at the narrowest point (x=0)
    # This ensures a physical gap of 'center_gap' between the inner edges.
    y_center = (center_gap / 2) + (wg_width / 2)  # 0.15 + 0.4 = 0.55
    
    # y_edge: vertical position of the waveguide centers at the ends (x=±9)
    # We place them so the outer edge is near the 3um boundary (y=±1.5)
    y_edge = 1.45 - (wg_width / 2) # 1.45 - 0.4 = 1.05
    
    # dy: total vertical change for the S-bend segment
    dy = y_edge - y_center 
    dx = total_width / 2
    
    # 3. Define the cross-section
    xs = gf.cross_section.strip(width=wg_width, layer=(1, 0))
    
    # 4. Create the S-bend segment
    # This component starts at (0,0) and ends at (dx, dy) with zero slope at both ends.
    s_segment = gf.components.bend_s(size=(dx, dy), cross_section=xs)
    
    # 5. Assemble the four quadrants
    # We place the ports precisely at x=0 to ensure perfect continuity.
    
    # --- TOP ARM ---
    # Top-Right: starts at center, curves UP to the right
    tr = c << s_segment
    tr.move((0, y_center))
    
    # Top-Left: mirror Top-Right across the Y-axis
    tl = c << s_segment
    tl.mirror(p1=(0, 0), p2=(0, 1))
    tl.move((0, y_center))
    
    # --- BOTTOM ARM ---
    # Bottom-Right: mirror Top-Right across the X-axis
    br = c << s_segment
    br.mirror(p1=(0, 0), p2=(1, 0))
    br.move((0, -y_center))
    
    # Bottom-Left: mirror Top-Left across the X-axis
    bl = c << s_segment
    bl.mirror(p1=(0, 0), p2=(0, 1)) # Horizontal flip
    bl.mirror(p1=(0, 0), p2=(1, 0)) # Vertical flip
    bl.move((0, -y_center))
    
    return c

if __name__ == "__main__":
    # Instantiate the component
    component = wavy_coupler_geometry()
    
    # Save to GDS file
    component.write_gds("wavy_coupler_v4.gds")
    
    # Visualize
    component.show()