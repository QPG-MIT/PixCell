import gdsfactory as gf

@gf.cell
def device_quatrefoil():
    """
    Recreates the quatrefoil-shaped device geometry with improved proportions based on target image analysis.
    
    Key Adjustments:
    - Increased petal minor radius (0.32 -> 0.46) to match the "plump" almond shape observed in the target.
    - Adjusted stick length (0.45 -> 0.38) to better match the visual ratio between the stick and petal.
    - Tuned center overlap to ensure robust connectivity while maintaining the distinct "pinched" center intersection.
    """
    # 1. Define Design Parameters
    # Footprint constraint: 4.7 x 4.7 um
    total_footprint = 4.7
    half_fp = total_footprint / 2  # 2.35 um
    
    # Stick (stub) dimensions
    # Visual estimate: Stick is relatively short compared to the petal length.
    stick_length = 0.38
    stick_width = 0.12
    
    # Stick placement
    # The stick is centered such that its outer edge aligns with the footprint boundary (2.35).
    # Center position = 2.35 - (0.38 / 2) = 2.16
    stick_center_pos = half_fp - (stick_length / 2)
    
    # The inner edge of the stick is at 2.35 - 0.38 = 1.97
    stick_inner_edge = half_fp - stick_length
    
    # Petal Geometry
    # The petal tip must overlap the stick slightly (0.03um) to ensure a merged polygon.
    overlap_stick = 0.03
    petal_tip_pos = stick_inner_edge + overlap_stick # ~2.00 um
    
    # Center overlap: 
    # Controls how much the petals merge at the center. 
    # A small overlap ensures the intersection remains sharp ("pinched").
    center_overlap = 0.12
    
    # Calculate Ellipse Dimensions
    # The ellipse major axis spans from inside the center (negative coordinate) to the tip.
    # Length = tip_position + center_overlap
    petal_long_axis = petal_tip_pos + center_overlap 
    petal_r_major = petal_long_axis / 2
    
    # Shift calculation: 
    # We place the ellipse center so the outer tip lands at `petal_tip_pos`.
    # Center relative to origin = Tip - Radius
    petal_shift = petal_tip_pos - petal_r_major
    
    # Minor radius: Controls the "fatness" of the petal.
    # Target appears to have an aspect ratio ~2:1 (Length ~2.0, Width ~1.0).
    # Radius ~0.46 gives a width of 0.92, which matches the target well.
    petal_r_minor = 0.46
    
    layer = (1, 0)

    # 2. Create Primitives
    c_temp = gf.Component("temp_assembly")
    
    # Primitives
    # Vertical Petal (Major axis along Y)
    e_vert = gf.components.ellipse(radii=(petal_r_minor, petal_r_major), layer=layer)
    # Horizontal Petal (Major axis along X)
    e_horiz = gf.components.ellipse(radii=(petal_r_major, petal_r_minor), layer=layer)
    
    r_horiz = gf.components.rectangle(size=(stick_length, stick_width), layer=layer, centered=True)
    r_vert = gf.components.rectangle(size=(stick_width, stick_length), layer=layer, centered=True)

    # 3. Assemble References
    
    # -- Petals --
    # North
    p_n = c_temp << e_vert
    p_n.movey(petal_shift)
    
    # South
    p_s = c_temp << e_vert
    p_s.movey(-petal_shift)
    
    # East
    p_e = c_temp << e_horiz
    p_e.movex(petal_shift)
    
    # West
    p_w = c_temp << e_horiz
    p_w.movex(-petal_shift)
    
    # -- Sticks --
    # North Stick
    s_n = c_temp << r_vert
    s_n.movey(stick_center_pos)
    
    # South Stick
    s_s = c_temp << r_vert
    s_s.movey(-stick_center_pos)
    
    # East Stick
    s_e = c_temp << r_horiz
    s_e.movex(stick_center_pos)
    
    # West Stick
    s_w = c_temp << r_horiz
    s_w.movex(-stick_center_pos)

    # 4. Boolean Operation
    # Flatten the assembly into a single clean polygon
    c_final = gf.boolean(c_temp, c_temp, operation='or', layer=layer)
    
    # 5. Add Ports
    c_final.add_port("o1", center=(-half_fp, 0), width=stick_width, orientation=180, layer=layer)
    c_final.add_port("o2", center=(half_fp, 0), width=stick_width, orientation=0, layer=layer)
    c_final.add_port("o3", center=(0, half_fp), width=stick_width, orientation=90, layer=layer)
    c_final.add_port("o4", center=(0, -half_fp), width=stick_width, orientation=270, layer=layer)
    
    c_final.name = "quatrefoil_device"
    return c_final

if __name__ == "__main__":
    component = device_quatrefoil()
    component.show()
    component.write_gds("quatrefoil_device.gds")