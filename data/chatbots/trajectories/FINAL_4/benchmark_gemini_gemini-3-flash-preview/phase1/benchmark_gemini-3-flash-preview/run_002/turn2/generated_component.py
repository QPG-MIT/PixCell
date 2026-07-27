import gdsfactory as gf

@gf.cell
def wavy_coupler_geometry():
    """
    Recreates the wavy waveguide geometry from the image.
    Adjusted parameters to ensure a clear gap at the center and 
    smooth adiabatic transitions using parametric S-bends.
    """
    c = gf.Component("wavy_coupler")
    
    # 1. Dimensions based on the 18um x 3um footprint constraint
    total_width = 18.0
    total_height = 3.0
    
    # 2. Geometric tuning to match the visual proportions of the original
    # We reduce the width and increase the gap to prevent the 'merging' effect.
    wg_width = 0.5
    center_gap = 0.6  # Increased gap to ensure separation in the middle
    
    # Calculate key vertical coordinates for the center-lines
    # Junction (midpoint) center-line:
    y_mid = (center_gap / 2) + (wg_width / 2)  # e.g., 0.3 + 0.25 = 0.55
    # End-point center-line:
    y_end = (total_height / 2) - (wg_width / 2) # e.g., 1.5 - 0.25 = 1.25
    
    # Vertical shift for each S-bend segment
    dy = y_end - y_mid 
    dx = total_width / 2
    
    # 3. Define the cross-section
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))
    
    # 4. Create the parametric S-bend primitive
    # This segment curves from (0,0) to (dx, dy) with 0-slope at both ends
    s_segment = gf.components.bend_s(size=(dx, dy), cross_section=xs)
    
    # 5. Assemble the four quadrants to create the two mirrored arms
    
    # --- TOP ARM ---
    # Top-Right segment: starts at center, curves UP to the right
    tr = c.add_ref(s_segment)
    tr.move((0, y_mid))
    
    # Top-Left segment: starts at center, curves UP to the left
    tl = c.add_ref(s_segment)
    tl.mirror(p1=(0, 0), p2=(0, 1)) # Mirror horizontally across Y-axis
    tl.move((0, y_mid))
    
    # --- BOTTOM ARM ---
    # Bottom-Right segment: starts at center, curves DOWN to the right
    br = c.add_ref(s_segment)
    br.mirror(p1=(0, 0), p2=(1, 0)) # Mirror vertically across X-axis
    br.move((0, -y_mid))
    
    # Bottom-Left segment: starts at center, curves DOWN to the left
    bl = c.add_ref(s_segment)
    bl.mirror(p1=(0, 0), p2=(0, 1)) # Mirror the bottom-right horizontally
    bl.move((0, -y_mid))
    
    return c

if __name__ == "__main__":
    # Create the component
    component = wavy_coupler_geometry()
    
    # Save the GDS
    component.write_gds("wavy_coupler_fixed.gds")
    
    # Display the result
    component.show()