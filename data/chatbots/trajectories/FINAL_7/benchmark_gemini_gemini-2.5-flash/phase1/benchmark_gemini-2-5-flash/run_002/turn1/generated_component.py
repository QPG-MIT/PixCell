import gdsfactory as gf
import numpy as np

@gf.cell
def device_from_image():
    c = gf.Component("device_from_image")
    layer_black = (1, 0) # GDS layer for the black material

    # Define overall dimensions from footprint
    # Footprint is 3.0 x 5.5 um
    total_width = 3.0
    total_height = 5.5
    center_x, center_y = 0, 0

    # 1. Parameters for the Outer Ellipse
    # Radii should match the total_width/2 and total_height/2 for the bounding box
    rx_outer = total_width / 2  # 1.5 um
    ry_outer = total_height / 2 # 2.75 um

    # 2. Parameters for the inner horizontal bars
    bar_width = 0.5  # Thickness of the black bars
    central_gap_y = 0.5 # White gap between the two bars

    # Y-positions for the center of the bars
    y_top_bar_center = central_gap_y / 2 + bar_width / 2 # 0.5
    y_bottom_bar_center = -(central_gap_y / 2 + bar_width / 2) # -0.5

    # 3. Parameters for the holes in the bars
    hole_width = 0.3
    hole_height = 0.3
    hole_spacing_x = 0.6  # Center-to-center spacing of holes

    # 4. Parameters for the straight central part of the bars and flares
    straight_bar_length_x = 1.2 # From x = -0.6 to 0.6
    x_bar_end_straight = straight_bar_length_x / 2 # 0.6

    # X-coordinate where the taper reaches its widest point / connects to the ellipse's curvature
    x_connect_flare_abs = 1.3
    flare_length = x_connect_flare_abs - x_bar_end_straight # 1.3 - 0.6 = 0.7

    # Calculate the Y-coordinate on the ellipse at `x_connect_flare_abs`
    # Ellipse equation: x^2/rx^2 + y^2/ry^2 = 1 => y = ry * sqrt(1 - (x/rx)^2)
    y_ellipse_at_flare_x = ry_outer * np.sqrt(1 - (x_connect_flare_abs / rx_outer)**2)

    # Calculate `width2` for the top bar's flare:
    # The flare extends from the bottom edge of the bar (y_top_bar_center - bar_width/2 = 0.25)
    # up to the ellipse's y-coordinate (y_ellipse_at_flare_x).
    flare_width_end_top = y_ellipse_at_flare_x - (y_top_bar_center - bar_width/2)

    # Calculate `width2` for the bottom bar's flare:
    # The flare extends from the top edge of the bar (y_bottom_bar_center + bar_width/2 = -0.25)
    # down to the ellipse's negative y-coordinate (-y_ellipse_at_flare_x).
    flare_width_end_bottom = (y_bottom_bar_center + bar_width/2) - (-y_ellipse_at_flare_x)

    # --- Construct the geometry using boolean operations ---

    # We will collect all black shapes, union them, then subtract the holes.
    black_parts_to_union = gf.Component("black_parts_for_union")

    # Add outer ellipse
    ellipse_ref = black_parts_to_union << gf.components.ellipse(radii=(rx_outer, ry_outer), layer=layer_black)

    # Top bar central straight part
    central_bar_top_comp = gf.components.rectangle(
        size=(straight_bar_length_x, bar_width),
        centered=True,
        layer=layer_black
    )
    central_bar_top_ref = black_parts_to_union << central_bar_top_comp
    central_bar_top_ref.movey(y_top_bar_center)

    # Bottom bar central straight part
    central_bar_bottom_comp = gf.components.rectangle(
        size=(straight_bar_length_x, bar_width),
        centered=True,
        layer=layer_black
    )
    central_bar_bottom_ref = black_parts_to_union << central_bar_bottom_comp
    central_bar_bottom_ref.movey(y_bottom_bar_center)

    # --- Tapered (Flared) sections for Top Bar ---
    # Left flare for top bar
    flare_left_top_comp = gf.components.taper(
        length=flare_length,
        width1=bar_width,
        width2=flare_width_end_top,
        layer=layer_black
    )
    flare_left_top_ref = black_parts_to_union << flare_left_top_comp
    flare_left_top_ref.mirror((0, 1)) # Mirror horizontally: narrow end ('o1') is now on the right

    # Calculate target connection point (center of the left edge of the central top bar)
    target_x_lt = central_bar_top_ref.x - straight_bar_length_x / 2
    target_y_lt = central_bar_top_ref.y # y-center of the central bar
    flare_left_top_ref.connect("o1", (target_x_lt, target_y_lt))

    # Right flare for top bar
    flare_right_top_comp = gf.components.taper(
        length=flare_length,
        width1=bar_width,
        width2=flare_width_end_top,
        layer=layer_black
    )
    flare_right_top_ref = black_parts_to_union << flare_right_top_comp
    
    # Calculate target connection point (center of the right edge of the central top bar)
    target_x_rt = central_bar_top_ref.x + straight_bar_length_x / 2
    target_y_rt = central_bar_top_ref.y # y-center of the central bar
    flare_right_top_ref.connect("o1", (target_x_rt, target_y_rt))


    # --- Tapered (Flared) sections for Bottom Bar ---
    # Left flare for bottom bar
    flare_left_bottom_comp = gf.components.taper(
        length=flare_length,
        width1=bar_width,
        width2=flare_width_end_bottom,
        layer=layer_black
    )
    flare_left_bottom_ref = black_parts_to_union << flare_left_bottom_comp
    flare_left_bottom_ref.mirror((0, 1)) # Mirror horizontally: narrow end ('o1') is now on the right
    
    # Calculate target connection point (center of the left edge of the central bottom bar)
    target_x_lb = central_bar_bottom_ref.x - straight_bar_length_x / 2
    target_y_lb = central_bar_bottom_ref.y # y-center of the central bar
    flare_left_bottom_ref.connect("o1", (target_x_lb, target_y_lb))

    # Right flare for bottom bar
    flare_right_bottom_comp = gf.components.taper(
        length=flare_length,
        width1=bar_width,
        width2=flare_width_end_bottom,
        layer=layer_black
    )
    flare_right_bottom_ref = black_parts_to_union << flare_right_bottom_comp
    
    # Calculate target connection point (center of the right edge of the central bottom bar)
    target_x_rb = central_bar_bottom_ref.x + straight_bar_length_x / 2
    target_y_rb = central_bar_bottom_ref.y # y-center of the central bar
    flare_right_bottom_ref.connect("o1", (target_x_rb, target_y_rb))

    # --- Perform boolean union (OR) on all black components ---
    unioned_black_shape = gf.boolean(black_parts_to_union, operation="or", layer=layer_black)
    
    # --- Create holes to subtract ---
    holes_to_subtract = gf.Component("holes_to_subtract")

    # Top bar holes
    hole1_top_cutout = gf.components.rectangle(size=(hole_width, hole_height), centered=True, layer=layer_black)
    hole2_top_cutout = gf.components.rectangle(size=(hole_width, hole_height), centered=True, layer=layer_black)
    holes_to_subtract << hole1_top_cutout.move(center_x - hole_spacing_x / 2, y_top_bar_center)
    holes_to_subtract << hole2_top_cutout.move(center_x + hole_spacing_x / 2, y_top_bar_center)

    # Bottom bar holes
    hole1_bottom_cutout = gf.components.rectangle(size=(hole_width, hole_height), centered=True, layer=layer_black)
    hole2_bottom_cutout = gf.components.rectangle(size=(hole_width, hole_height), centered=True, layer=layer_black)
    holes_to_subtract << hole1_bottom_cutout.move(center_x - hole_spacing_x / 2, y_bottom_bar_center)
    holes_to_subtract << hole2_bottom_cutout.move(center_x + hole_spacing_x / 2, y_bottom_bar_center)

    # --- Subtract the holes from the unioned black shape ---
    final_device_component = gf.boolean(unioned_black_shape, holes_to_subtract, operation="not", layer=layer_black)

    # Add the final combined and cut shape to the main component 'c'
    c.add_ref(final_device_component)

    return c

# Create and save the device
if __name__ == "__main__":
    device = device_from_image()
    
    # Check the footprint
    bbox = device.bounding_box()
    width_check = round(bbox[1][0] - bbox[0][0], 2)
    height_check = round(bbox[1][1] - bbox[0][1], 2)
    print(f"Device Bounding Box: {width_check}x{height_check} um")
    
    device.show() # To visualize in KLayout
    device.write_gds("device_from_image.gds")