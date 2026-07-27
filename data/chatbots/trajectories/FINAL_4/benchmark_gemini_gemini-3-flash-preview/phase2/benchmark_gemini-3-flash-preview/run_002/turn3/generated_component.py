import gdsfactory as gf

@gf.cell
def wavy_coupler_geometry():
    """
    Recreates the wavy waveguide coupler with perfect vertical and horizontal symmetry.
    Uses S-bend primitives to ensure zero-slope transitions at the center and edges.
    """
    c = gf.Component("wavy_coupler_v3")
    
    # 1. Dimensions based on the 18um x 3um footprint constraint
    total_width = 18.0
    total_height = 3.0
    
    # 2. Geometric tuning for visual match
    # width ~ 0.6um and gap ~ 0.4um provides the thick, closely-spaced look of the target.
    wg_width = 0.6
    center_gap = 0.4 
    
    # Calculate vertical offsets for the centerlines
    # y_center: The vertical position of the waveguide centers at the narrowest point (x=0)
    y_center = (center_gap / 2) + (wg_width / 2)  # 0.2 + 0.3 = 0.5
    
    # y_edge: The vertical position of the waveguide centers at the ends (x=±9)
    # We place them near the edge of the 3um footprint
    y_edge = (total_height / 2) - (wg_width / 2)   # 1.5 - 0.3 = 1.2
    
    # dy: The total vertical rise/fall for each S-bend segment
    dy = y_edge - y_center 
    dx = total_width / 2
    
    # 3. Define the cross-section
    xs = gf.cross_section.strip(width=wg_width, layer=(1, 0))
    
    # 4. Create the basic S-bend segment
    # This component naturally starts at (0,0) and ends at (dx, dy)
    s_segment = gf.components.bend_s(size=(dx, dy), cross_section=xs)
    
    # 5. Assemble the quadrants
    # By mirroring correctly across the X and Y axes, we ensure a perfect junction at the center.
    
    # --- TOP ARM ---
    # Top-Right: starts at center, curves UP to the right
    tr = c << s_segment
    tr.movey(y_center)
    
    # Top-Left: mirror Top-Right across the Y-axis (keep o1 at center)
    tl = c << s_segment
    tl.mirror(p1=(0, 0), p2=(0, 1))
    tl.movey(y_center)
    
    # --- BOTTOM ARM ---
    # Bottom-Right: mirror Top-Right across the X-axis (curves DOWN to the right)
    br = c << s_segment
    br.mirror(p1=(0, 0), p2=(1, 0))
    br.movey(-y_center)
    
    # Bottom-Left: mirror Bottom-Right across the Y-axis (curves DOWN to the left)
    bl = c << s_segment
    bl.mirror(p1=(0, 0), p2=(0, 1)) # Horizontal flip
    bl.mirror(p1=(0, 0), p2=(1, 0)) # Vertical flip
    bl.movey(-y_center)
    
    return c

if __name__ == "__main__":
    # Instantiate the component
    component = wavy_coupler_geometry()
    
    # Save to GDS file
    component.write_gds("wavy_coupler_final.gds")
    
    # Visualize
    component.show()