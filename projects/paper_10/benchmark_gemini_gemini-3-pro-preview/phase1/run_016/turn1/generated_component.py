import gdsfactory as gf
import numpy as np

@gf.cell
def device_heater_structure():
    """
    Recreates the heater/modulator structure from the image within a 3x5.5um footprint.
    Uses gf.boolean for geometry composition to avoid attribute errors.
    """
    # 1. Define Parameters
    # --------------------
    layer_main = (1, 0)
    
    # Outer Dimensions
    width_total = 5.5
    height_total = 3.0
    
    # Ring Geometry
    ring_width = 0.45
    radius_outer = height_total / 2.0             # 1.5 um
    radius_center = radius_outer - ring_width/2.0
    straight_length = width_total - height_total  # 2.5 um
    
    # Inner Arm Geometry
    arm_y_offset = 0.75        # Vertical distance from center to arm axis
    pad_width = 0.75           # Width of the rectangular blocks
    pad_height = 0.55          # Height of the rectangular blocks
    bridge_width = 0.2         # Gap between pads filled by bridge
    
    # Hole Geometry (Windows)
    hole_width = 0.4
    hole_height = 0.25

    # 2. Create Positive Geometry (Material)
    # --------------------------------------
    c_pos = gf.Component("Positive_Mask")

    # A. Racetrack Ring using Path
    # We create a path and extrude it
    p = gf.Path()
    p.append(gf.path.straight(length=straight_length))
    p.append(gf.path.arc(radius=radius_center, angle=180))
    p.append(gf.path.straight(length=straight_length))
    p.append(gf.path.arc(radius=radius_center, angle=180))
    
    xs_ring = gf.cross_section.cross_section(width=ring_width, layer=layer_main)
    ring = c_pos << gf.path.extrude(p, cross_section=xs_ring)
    ring.center = (0, 0)

    # B. Inner Pads and Bridges
    pad_shape = gf.components.rectangle(size=(pad_width, pad_height), layer=layer_main, centered=True)
    bridge_shape = gf.components.rectangle(size=(bridge_width + 0.1, pad_height - 0.15), layer=layer_main, centered=True)
    
    # Function to place one arm set
    def add_arm_pos(y_pos):
        # Left Pad
        pl = c_pos << pad_shape
        pl.move((-pad_width/2 - bridge_width/2, y_pos))
        # Right Pad
        pr = c_pos << pad_shape
        pr.move((pad_width/2 + bridge_width/2, y_pos))
        # Bridge
        br = c_pos << bridge_shape
        br.move((0, y_pos))
        
        # Add Tapers (Polygons connecting pads to ring)
        # Pad outer x is approx 0.85. Ring inner straight wall ends at x=1.25.
        # We flare out from the pad corners to the ring wall.
        
        # Right Taper Points
        x_pad_edge = pad_width + bridge_width/2
        x_ring_start = straight_length / 2.0
        
        # Taper connecting Right Pad to Right Arc
        pts_right = [
            (x_pad_edge, y_pos + pad_height/2),       # Top-right of pad
            (x_pad_edge, y_pos - pad_height/2),       # Bot-right of pad
            (x_ring_start + 0.15, y_pos - 0.3),       # Bottom connection to ring
            (x_ring_start + 0.15, y_pos + 0.3),       # Top connection to ring
        ]
        c_pos.add_polygon(pts_right, layer=layer_main)
        
        # Left Taper Points (Mirrored)
        pts_left = [(-x, y) for x, y in pts_right]
        c_pos.add_polygon(pts_left, layer=layer_main)

    # Add Top and Bottom Arms
    add_arm_pos(arm_y_offset)
    add_arm_pos(-arm_y_offset)

    # 3. Create Negative Geometry (Holes)
    # -----------------------------------
    c_neg = gf.Component("Negative_Mask")
    hole_shape = gf.components.rectangle(size=(hole_width, hole_height), layer=layer_main, centered=True)

    def add_arm_holes(y_pos):
        # Left Hole
        hl = c_neg << hole_shape
        hl.move((-pad_width/2 - bridge_width/2, y_pos))
        # Right Hole
        hr = c_neg << hole_shape
        hr.move((pad_width/2 + bridge_width/2, y_pos))
        
    add_arm_holes(arm_y_offset)
    add_arm_holes(-arm_y_offset)

    # 4. Final Boolean (Positive NOT Negative)
    # ----------------------------------------
    # This merges all positive shapes and subtracts the holes in one clean operation
    c_final = gf.boolean(A=c_pos, B=c_neg, operation="not", layer=layer_main)
    
    # 5. Add Ports (Optional, based on ring ends)
    c_final.add_port("o1", center=(-width_total/2, 0), width=ring_width, orientation=180, layer=layer_main)
    c_final.add_port("o2", center=(width_total/2, 0), width=ring_width, orientation=0, layer=layer_main)
    
    return c_final

# Create and verify
if __name__ == "__main__":
    device = device_heater_structure()
    device.show() # Opens in KLayout
    device.write_gds("heater_structure_corrected.gds")
    
    # Verification
    print(f"Device Name: {device.name}")
    print(f"Bbox: {device.bbox}")