import gdsfactory as gf

@gf.cell
def make_device():
    """
    Recreates the device using parametric primitives.
    Footprint: 5.5 um x 3.0 um
    """
    c = gf.Component("recreated_device")
    layer = (1, 0)
    
    # --- 1. Dimensions based on footprint [5.5, 3.0] ---
    total_width = 5.5
    total_height = 3.0
    r_outer = total_height / 2  # 1.5 um
    l_straight = total_width - 2 * r_outer  # 2.5 um
    ring_width = 0.45
    
    # --- 2. Create the Outer Racetrack Ring ---
    # We use the Path system to define the centerline and extrude it.
    # Centerline radius = outer_radius - half_width
    r_center = r_outer - (ring_width / 2)
    p_ring = gf.Path()
    p_ring.append(gf.path.straight(length=l_straight))
    p_ring.append(gf.path.arc(radius=r_center, angle=180))
    p_ring.append(gf.path.straight(length=l_straight))
    p_ring.append(gf.path.arc(radius=r_center, angle=180))
    
    # Extrude and add as a reference
    ring_comp = gf.path.extrude(p_ring, width=ring_width, layer=layer)
    ring_ref = c << ring_comp
    # Center the ring at (0,0)
    ring_ref.move((-l_straight / 2, r_center))

    # --- 3. Central Hubs (connecting blocks) ---
    hub_width = 0.4
    hub_height = 0.8
    hub_dist = 2.0 # distance from center to hub center
    hub_rect = gf.components.rectangle(size=(hub_width, hub_height), centered=True, layer=layer)
    
    h_left = c << hub_rect
    h_left.movex(-hub_dist)
    h_right = c << hub_rect
    h_right.movex(hub_dist)

    # --- 4. Bowtie Rails and Heaters ---
    rail_w = 0.18
    rail_y = 0.65 # Vertical offset from center
    
    # Create the "bowtie" path for one rail
    pts = [(-hub_dist, 0), (-1.2, rail_y), (1.2, rail_y), (hub_dist, 0)]
    rail_path = gf.path.smooth(points=pts, radius=0.4)
    rail_comp = gf.path.extrude(rail_path, width=rail_w, layer=layer)
    
    # Heater: A hollow rectangle created using Boolean logic
    outer_box = gf.components.rectangle(size=(0.85, 0.45), centered=True, layer=layer)
    inner_box = gf.components.rectangle(size=(0.6, 0.25), centered=True, layer=layer)
    heater_unit = gf.boolean(outer_box, inner_box, operation="not", layer=layer)
    
    # Create a sub-assembly for the top rail + heaters
    rail_group = gf.Component("rail_group")
    rail_group << rail_comp
    # Add two heaters to the horizontal segment
    h1 = rail_group << heater_unit
    h1.move((-0.6, rail_y))
    h2 = rail_group << heater_unit
    h2.move((0.6, rail_y))
    
    # Add the top rail assembly to main component
    c << rail_group
    
    # Add the bottom rail assembly by mirroring/rotating a reference
    bottom_rail = c << rail_group
    bottom_rail.mirror_y() # Flips to the bottom half

    return c

if __name__ == "__main__":
    # Create the component
    device = make_device()
    
    # 1. EXPLICITLY WRITE TO GDS FILE
    filename = "recreated_device.gds"
    device.write_gds(filename)
    print(f"Successfully produced GDS file: {filename}")
    
    # 2. Check dimensions
    bbox = device.bbox
    width = bbox[1][0] - bbox[0][0]
    height = bbox[1][1] - bbox[0][1]
    print(f"Final Footprint: {width:.2f} um x {height:.2f} um")

    # 3. Optional: Visual check (requires KLayout installed)
    try:
        device.show()
    except Exception:
        print("Note: .show() failed (likely no GDS viewer installed), but the GDS file was written.")