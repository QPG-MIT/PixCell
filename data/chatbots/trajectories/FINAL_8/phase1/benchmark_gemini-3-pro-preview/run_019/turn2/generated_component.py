import gdsfactory as gf
import numpy as np

@gf.cell
def grating_coupler_device_v2():
    """
    Refined recreation of the multi-rail directional coupler.
    Features:
    1. Central Bus: 5 continuous parallel straight waveguides.
    2. Outer Rails: Thick waveguides that flare out (S-bend) at the ends and are straight in the center.
    3. Fins: Inner straight waveguides of varying lengths nested in the coupling region.
    """
    c = gf.Component()
    
    # ==========================================
    # 1. Design Parameters
    # ==========================================
    # Constraints
    device_length = 120.0
    device_height_limit = 4.0
    
    # Waveguide Dimensions (in microns)
    center_wg_width = 0.12
    gap = 0.08
    outer_wg_width = 0.5    # Thicker cladding rail
    
    # Longitudinal Layout
    # The device has a straight "coupling region" in the middle, and bends at ends.
    coupling_length = 50.0  
    bend_length = (device_length - coupling_length) / 2
    
    # Cross Sections
    xs_center = gf.cross_section.cross_section(width=center_wg_width, layer=(1, 0))
    xs_fin = gf.cross_section.cross_section(width=center_wg_width, layer=(1, 0))
    xs_outer = gf.cross_section.cross_section(width=outer_wg_width, layer=(1, 0))

    # ==========================================
    # 2. Central Bus Construction
    # ==========================================
    # 5 parallel rails centered at Y=0
    num_center_rails = 5
    center_pitch = center_wg_width + gap
    
    # Calculate the total height of the center bundle to determine Y positions
    total_center_height = num_center_rails * center_wg_width + (num_center_rails - 1) * gap
    y_start_center = -(total_center_height / 2) + center_wg_width / 2
    
    # Create the single straight waveguide primitive
    wg_straight = gf.components.straight(length=device_length, cross_section=xs_center)
    
    for i in range(num_center_rails):
        y_pos = y_start_center + i * center_pitch
        ref = c << wg_straight
        ref.movey(y_pos)

    # ==========================================
    # 3. Outer Assembly (Top Half)
    # ==========================================
    # The outer assembly consists of "Fins" (straight lines) and the "Outer Rail" (Curved)
    
    # A. Place Fins
    # We place fins starting just above the central bus
    y_cursor = (total_center_height / 2) + gap
    
    # Fins get progressively shorter as they move outward (nested inside the curve)
    # We align them to the center of the device
    fin_lengths = [coupling_length + 30, coupling_length + 15, coupling_length]
    
    for length in fin_lengths:
        y_fin_center = y_cursor + center_wg_width / 2
        
        # Create Fin
        fin = c << gf.components.straight(length=length, cross_section=xs_fin)
        fin.center = (0, y_fin_center) # Center the fin at (x=0, y=current)
        
        # Move cursor up for next element
        y_cursor += (center_wg_width + gap)

    # B. Construct Flared Outer Rail
    # This waveguide starts high (at device edge), swoops down to coupling gap, goes straight, then swoops up.
    
    # Y-Coordinates for the outer rail
    y_coupling_inner = y_cursor # The gap starts where the last fin ended
    y_coupling_center = y_coupling_inner + outer_wg_width / 2
    
    # The rail should flare out to the limit of the footprint (y = +/- 2.0)
    y_max_center = (device_height_limit / 2) - (outer_wg_width / 2)
    
    # Generate the Path Points explicitly for the S-Bend -> Straight -> S-Bend shape
    num_pts = 100
    
    # Helper for Cosine S-Bend (Ease-in-Ease-out transition)
    def sbend_y(t, y_start, y_end):
        return y_start + (y_end - y_start) * (1 - np.cos(np.pi * t)) / 2

    # Part 1: Left Flare (High to Low)
    x_1 = np.linspace(-device_length/2, -coupling_length/2, num_pts)
    t_1 = np.linspace(0, 1, num_pts)
    y_1 = sbend_y(t_1, y_max_center, y_coupling_center)
    
    # Part 2: Center Straight (Low, constant)
    x_2 = np.linspace(-coupling_length/2, coupling_length/2, num_pts)
    y_2 = np.full_like(x_2, y_coupling_center)
    
    # Part 3: Right Flare (Low to High)
    x_3 = np.linspace(coupling_length/2, device_length/2, num_pts)
    t_3 = np.linspace(0, 1, num_pts)
    y_3 = sbend_y(t_3, y_coupling_center, y_max_center)
    
    # Concatenate to form full path
    x_path = np.concatenate([x_1, x_2[1:], x_3[1:]])
    y_path = np.concatenate([y_1, y_2[1:], y_3[1:]])
    path_points = list(zip(x_path, y_path))
    
    # Extrude the path
    outer_path = gf.Path(path_points)
    outer_rail = c << gf.path.extrude(outer_path, cross_section=xs_outer)

    # ==========================================
    # 4. Mirror for Bottom Half
    # ==========================================
    # To create the bottom half, we mirror the Top Fins and Top Outer Rail
    
    # Mirror Fins
    # We recalculate positions negatively to be explicit
    y_cursor_bot = -((total_center_height / 2) + gap)
    for length in fin_lengths:
        y_fin_center = y_cursor_bot - center_wg_width / 2
        fin = c << gf.components.straight(length=length, cross_section=xs_fin)
        fin.center = (0, y_fin_center)
        y_cursor_bot -= (center_wg_width + gap)
        
    # Mirror Outer Rail
    # We can simply clone the top rail and apply a mirror transform
    outer_rail_bot = c << gf.path.extrude(outer_path, cross_section=xs_outer)
    outer_rail_bot.mirror(p1=(0,0), p2=(1,0)) # Mirror across X-axis (y=0)

    return c

if __name__ == "__main__":
    # Create the device
    device = grating_coupler_device_v2()
    
    # Save to GDS
    device.write_gds("recreated_device_v2.gds")
    
    # Display
    device.show()