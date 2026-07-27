import gdsfactory as gf

@gf.cell
def wavy_coupler_geometry():
    """
    Recreates the wavy waveguide geometry from the image using the 
    bend_s parametric primitive. Positions are calculated to fit 
    within the 18um x 3um footprint.
    """
    c = gf.Component("wavy_coupler")
    
    # Footprint constraints
    total_width = 18.0
    total_height = 3.0
    
    # Geometric parameters for the waveguides
    wg_width = 0.7
    center_gap = 0.2
    
    # Calculate the vertical shift (dy) for each S-bend segment
    # The waveguide center-line at the middle of the device:
    y_center_mid = (center_gap / 2) + (wg_width / 2)
    # The waveguide center-line at the far ends:
    y_center_end = (total_height / 2) - (wg_width / 2)
    
    dy = y_center_end - y_center_mid
    dx = total_width / 2
    
    # Define the cross-section
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))
    
    # Create the parametric S-bend primitive (half an arm)
    # By default, o1 is at (0, 0) and o2 is at (dx, dy)
    s_segment = gf.components.bend_s(size=(dx, dy), cross_section=xs)
    
    # --- TOP ARM ---
    # Top-Right segment
    tr = c << s_segment
    tr.move((0, y_center_mid)) # Moves junction to x=0, y=y_center_mid
    
    # Top-Left segment (Mirror Top-Right horizontally)
    tl = c << s_segment
    tl.mirror(p1=(0, 0), p2=(0, 1)) # Mirror across Y-axis
    tl.move((0, y_center_mid))
    
    # --- BOTTOM ARM ---
    # Bottom-Right segment (Mirror Top-Right vertically)
    br = c << s_segment
    br.mirror(p1=(0, 0), p2=(1, 0)) # Mirror across X-axis
    br.move((0, -y_center_mid))
    
    # Bottom-Left segment (Mirror Top-Left vertically)
    bl = c << s_segment
    bl.mirror(p1=(0, 0), p2=(0, 1))
    bl.mirror(p1=(0, 0), p2=(1, 0))
    bl.move((0, -y_center_mid))
    
    # Expose external ports (using strings to access ports is safe)
    # These ports are at the far left and right edges (+/- 9um)
    c.add_port("o1", port=tl.ports["o2"])
    c.add_port("o2", port=tr.ports["o2"])
    c.add_port("o3", port=bl.ports["o2"])
    c.add_port("o4", port=br.ports["o2"])
    
    return c

if __name__ == "__main__":
    # Instantiate the component
    device = wavy_coupler_geometry()
    
    # Write to GDS
    device.write_gds("wavy_coupler.gds")
    
    # Show the geometry (requires a GDS viewer like KLayout)
    device.show()