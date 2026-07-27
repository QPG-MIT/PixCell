import gdsfactory as gf
import numpy as np

@gf.cell
def racetrack_mzi_reconstructed():
    c = gf.Component()

    # --- 1. Key Dimensions ---
    # From image analysis and constraints
    total_length = 5.5
    total_height = 3.0
    
    # Radii and Widths
    radius_outer = total_height / 2      # 1.5 um
    bend_width = 0.6                     # Wide bend waveguide
    straight_width = 0.35                # Narrow straight waveguide
    
    # The center-line radius for the bend component
    radius_center = radius_outer - (bend_width / 2) # 1.2 um

    # Length of the straight section (between the bends)
    # The bend occupies 'radius_outer' width (1.5um) on each side
    straight_section_len = total_length - (2 * radius_outer) # 2.5 um
    
    # Coordinate calculations
    # The interface between bends and straight arms is at x = +/- (straight_len / 2)
    x_interface = straight_section_len / 2  # 1.25 um
    
    # Layer definition
    layer_main = (1, 0)

    # --- 2. Define Custom CrossSection ---
    # Allow small radius without validation error
    xs_bend = gf.cross_section.cross_section(
        width=bend_width,
        layer=layer_main,
        radius_min=0.1 
    )

    # --- 3. Create and Place Bends ---
    
    # LEFT BEND
    # Standard bend_circular(180) moves from (0,0) [East] to (0, 2R) [West], curving Left (x < 0).
    # We want it to connect to the bottom arm at (-1.25, -1.2) and top arm at (-1.25, 1.2).
    # Placing the start port at (-1.25, -1.2) creates the C-shape on the left.
    bend_l = c << gf.components.bend_circular(
        radius=radius_center, 
        angle=180, 
        cross_section=xs_bend
    )
    # Move the start port (o1) to the bottom-left interface
    bend_l.move(origin=(0,0), destination=(-x_interface, -radius_center))

    # RIGHT BEND
    # We take a standard bend and mirror it across the Y-axis.
    # Original: Start (0,0) East -> End (0, 2R) West. (Bulge Left).
    # Mirrored: Start (0,0) West -> End (0, 2R) East. (Bulge Right).
    # We want this to connect to the bottom arm at (1.25, -1.2).
    # Since the mirrored start port faces West, it will couple correctly to the arm coming from the left.
    bend_r = c << gf.components.bend_circular(
        radius=radius_center, 
        angle=180, 
        cross_section=xs_bend
    )
    bend_r.mirror() # Flips across x=0 line
    bend_r.move(origin=(0,0), destination=(x_interface, -radius_center))

    # --- 4. Create The Arms (Custom Polygons) ---
    # The arms consist of a straight section and a linear taper "neck" connecting to the bends.
    # We define vertices explicitly to ensure perfect connectivity.

    taper_len = 0.5
    inner_gap = 0.8  # Visual estimate of gap between arms
    
    # Y-coordinates for the Straight Section
    y_st_center = (inner_gap + straight_width) / 2
    y_st_top = y_st_center + straight_width/2
    y_st_bot = y_st_center - straight_width/2
    
    # Y-coordinates for the Bend Interface
    y_bend_center = radius_center
    y_bend_top = y_bend_center + bend_width/2
    y_bend_bot = y_bend_center - bend_width/2

    # X-coordinates
    x_left_bend = -x_interface              # -1.25
    x_left_straight = -x_interface + taper_len  # -0.75
    x_right_straight = x_interface - taper_len  # 0.75
    x_right_bend = x_interface              # 1.25

    # Vertices for Top Arm (CW order)
    points_top = [
        (x_left_bend, y_bend_top),          # Top-Left (at bend outer)
        (x_left_straight, y_st_top),        # Top-Left (taper end)
        (x_right_straight, y_st_top),       # Top-Right (taper start)
        (x_right_bend, y_bend_top),         # Top-Right (at bend outer)
        (x_right_bend, y_bend_bot),         # Bottom-Right (at bend inner)
        (x_right_straight, y_st_bot),       # Bottom-Right (taper start)
        (x_left_straight, y_st_bot),        # Bottom-Left (taper end)
        (x_left_bend, y_bend_bot)           # Bottom-Left (at bend inner)
    ]
    c.add_polygon(points_top, layer=layer_main)

    # Vertices for Bottom Arm (Mirror Top across X-axis)
    points_bot = [(x, -y) for x, y in points_top]
    c.add_polygon(points_bot, layer=layer_main)

    # --- 5. Add Heater Pads ---
    pad_w = 0.65
    pad_h = 0.6
    pad_spacing = 0.2
    
    # Pad geometry reference
    pad_ref = gf.components.rectangle(size=(pad_w, pad_h), layer=layer_main, centered=True)
    
    # Pad center X offset
    x_pad_center = (pad_spacing + pad_w) / 2
    
    # Place Pads (Top Arm)
    c.add_ref(pad_ref).move(( -x_pad_center, y_st_center ))
    c.add_ref(pad_ref).move(( x_pad_center, y_st_center ))
    
    # Place Pads (Bottom Arm)
    c.add_ref(pad_ref).move(( -x_pad_center, -y_st_center ))
    c.add_ref(pad_ref).move(( x_pad_center, -y_st_center ))

    return c

if __name__ == "__main__":
    device = racetrack_mzi_reconstructed()
    device.show()
    device.write_gds("racetrack_fixed.gds")
    
    # Print dimensions to confirm
    print(f"Device Size: {device.size_info.width:.2f} x {device.size_info.height:.2f} um")