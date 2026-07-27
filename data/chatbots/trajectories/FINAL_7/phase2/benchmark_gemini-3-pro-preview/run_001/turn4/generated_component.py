import gdsfactory as gf

@gf.cell
def device_heater_structure():
    """
    Recreates the heater/modulator structure with corrected "horizontal-to-curve"
    taper geometry to match the reference image's void shapes and gaps.
    """
    # 1. Define Parameters
    # --------------------
    layer_main = (1, 0)
    
    # Outer Dimensions
    width_total = 5.5
    height_total = 3.0
    
    # Ring Geometry
    # Thick ring trace
    ring_width = 0.55
    radius_outer = height_total / 2.0             # 1.5 um
    radius_center = radius_outer - ring_width/2.0
    straight_length = width_total - height_total  # 2.5 um
    
    # Inner Arm Geometry
    # Y-offset determines the gap between the two arms
    arm_y_offset = 0.62
    
    pad_width = 0.75
    pad_height = 0.52
    
    # Bridge geometry (thinner than pads to create notches)
    bridge_width = 0.25
    bridge_height = 0.30 
    
    # Holes (Windows)
    hole_width = 0.45
    hole_height = 0.25

    # 2. Create Positive Geometry (The Black Areas)
    # ---------------------------------------------
    c_pos = gf.Component("Positive_Mask")

    # A. Racetrack Ring
    p = gf.Path()
    p.append(gf.path.straight(length=straight_length))
    p.append(gf.path.arc(radius=radius_center, angle=180))
    p.append(gf.path.straight(length=straight_length))
    p.append(gf.path.arc(radius=radius_center, angle=180))
    
    xs_ring = gf.cross_section.cross_section(width=ring_width, layer=layer_main)
    ring = c_pos << gf.path.extrude(p, cross_section=xs_ring)
    ring.center = (0, 0)

    # B. Inner Arms Assembly
    pad_shape = gf.components.rectangle(size=(pad_width, pad_height), layer=layer_main, centered=True)
    bridge_shape = gf.components.rectangle(size=(bridge_width + 0.1, bridge_height), layer=layer_main, centered=True)
    
    def add_arm_pos(y_pos, mirror_y=False):
        """
        Adds one horizontal arm assembly.
        mirror_y: If True, reflects logic for the bottom arm.
        """
        # Calculate X positions
        x_pad_center_offset = pad_width/2 + bridge_width/2
        
        # 1. Pads
        pl = c_pos << pad_shape
        pl.move((-x_pad_center_offset, y_pos))
        pr = c_pos << pad_shape
        pr.move((x_pad_center_offset, y_pos))
        
        # 2. Bridge
        br = c_pos << bridge_shape
        br.move((0, y_pos))
        
        # 3. Connections to Ring (Tapers)
        # Geometry constants for the arm
        x_pad_edge = x_pad_center_offset + pad_width/2
        y_pad_top = y_pos + pad_height/2
        y_pad_bot = y_pos - pad_height/2
        
        # Taper End Point (Deep inside the ring curve)
        x_end = 2.05 
        
        # Define the Right-side Taper
        # For the Top Arm:
        # - Top Edge: Stays horizontal to create a clean gap with the ring straight section,
        #   eventually merging into the ring curve naturally.
        # - Bottom Edge: Slopes down towards y=0 to close the central void.
        
        if not mirror_y:
            # Top Arm Logic
            pts_right = [
                (x_pad_edge, y_pad_top),       # Top-Left (at Pad)
                (x_pad_edge, y_pad_bot),       # Bottom-Left (at Pad)
                (x_end, -0.05),                # Bottom-Right (Target past center to merge)
                (x_end, y_pad_top)             # Top-Right (Horizontal extension)
            ]
        else:
            # Bottom Arm Logic (Mirrored Y)
            pts_right = [
                (x_pad_edge, y_pad_bot),       # Bottom-Left (at Pad)
                (x_pad_edge, y_pad_top),       # Top-Left (at Pad)
                (x_end, y_pad_bot),            # Top-Right (Horizontal extension)
                (x_end, 0.05)                  # Bottom-Right (Target past center to merge)
            ]

        # Add Right Taper
        c_pos.add_polygon(pts_right, layer=layer_main)
        
        # Add Left Taper (Mirrored X)
        pts_left = [(-x, y) for x, y in pts_right]
        c_pos.add_polygon(pts_left, layer=layer_main)

    # Add Top Arm
    add_arm_pos(arm_y_offset, mirror_y=False)
    # Add Bottom Arm
    add_arm_pos(-arm_y_offset, mirror_y=True)

    # 3. Create Negative Geometry (Holes)
    # -----------------------------------
    c_neg = gf.Component("Negative_Mask")
    hole_shape = gf.components.rectangle(size=(hole_width, hole_height), layer=layer_main, centered=True)

    def add_arm_holes(y_pos):
        x_pad_center_offset = pad_width/2 + bridge_width/2
        hl = c_neg << hole_shape
        hl.move((-x_pad_center_offset, y_pos))
        hr = c_neg << hole_shape
        hr.move((x_pad_center_offset, y_pos))
        
    add_arm_holes(arm_y_offset)
    add_arm_holes(-arm_y_offset)

    # 4. Final Boolean Operation
    # --------------------------
    c_final = gf.boolean(A=c_pos, B=c_neg, operation="not", layer=layer_main)
    
    # 5. Add Ports
    c_final.add_port("o1", center=(-width_total/2, 0), width=ring_width, orientation=180, layer=layer_main)
    c_final.add_port("o2", center=(width_total/2, 0), width=ring_width, orientation=0, layer=layer_main)
    
    return c_final

if __name__ == "__main__":
    device = device_heater_structure()
    device.show()
    device.write_gds("heater_structure_final.gds")
    
    print(f"Device Name: {device.name}")
    print(f"BBox: {device.bbox}")