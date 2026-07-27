import gdsfactory as gf

@gf.cell
def apodized_symmetric_coupler():
    """
    Creates an apodized symmetrical directional coupler.
    Uses continuous waveguides with S-bends and boolean subtraction to perfectly 
    form the cropped boundary regions as constrained by the 120x4 footprint.
    """
    c = gf.Component("apodized_symmetric_coupler")
    wg_group = gf.Component("wg_group")

    # Target footprint constraints
    L_total = 120.0
    total_height = 4.0

    # Routing and cross-section parameters
    dx = 30.0  # Horizontal length of the S-bends
    L_straight = L_total - 2 * dx  # 60.0um straight coupling region in the center
    w_thin = 0.1  # Width of standard waveguides
    g = 0.1       # Gap between waveguides
    pitch = w_thin + g  # 0.2um pitch
    dy = 0.4      # Vertical shift of the outer waveguide groups at the ends
    W_thick = 3.0 # Over-sized width for the outer boundaries (to be clipped later)

    # We make the routing slightly longer than L_total so we can cleanly slice it with a boolean bounding box
    L_end_overshoot = 1.0 
    L_total_wg = L_total + 2 * L_end_overshoot

    def add_waveguide(y_center, width, dy_shift):
        """Helper to create a single waveguide track (straight or bent) symmetrically."""
        xs = gf.cross_section.cross_section(width=width, layer=(1, 0))

        if dy_shift == 0.0:
            # Central straight waveguides
            str_comp = gf.components.straight(length=L_total_wg, cross_section=xs)
            ref = wg_group << str_comp
            # Center the straight component at x=0
            ref.move((-L_total_wg / 2, y_center))
        else:
            # Outer bent waveguides
            # 1. Central straight section
            str_comp = gf.components.straight(length=L_straight, cross_section=xs)
            ref_str = wg_group << str_comp
            ref_str.move((-L_straight / 2, y_center))

            # 2. Right S-bend and overshoot
            s_right = gf.components.bend_s(size=(dx, dy_shift), cross_section=xs)
            ref_s_right = wg_group << s_right
            ref_s_right.connect('o1', ref_str.ports['o2'])

            end_right = gf.components.straight(length=L_end_overshoot, cross_section=xs)
            ref_end_right = wg_group << end_right
            ref_end_right.connect('o1', ref_s_right.ports['o2'])

            # 3. Left S-bend and overshoot
            s_left = gf.components.bend_s(size=(dx, -dy_shift), cross_section=xs)
            ref_s_left = wg_group << s_left
            ref_s_left.connect('o2', ref_str.ports['o1'])

            end_left = gf.components.straight(length=L_end_overshoot, cross_section=xs)
            ref_end_left = wg_group << end_left
            ref_end_left.connect('o1', ref_s_left.ports['o1'])

    # --- Build the 15 Waveguide Array ---
    
    # 1. Center Group: 5 perfectly straight thin waveguides
    for i in range(-2, 3):
        add_waveguide(i * pitch, w_thin, 0.0)

    # 2. Top Group: 4 thin + 1 thick waveguide, bending UP at the ends
    for i in range(3, 7):
        add_waveguide(i * pitch, w_thin, dy)
        
    # The top thick waveguide is oversized and shifted so its bottom gap remains consistent
    y_7 = 6 * pitch + w_thin/2 + g + W_thick/2
    add_waveguide(y_7, W_thick, dy)

    # 3. Bottom Group: 4 thin + 1 thick waveguide, bending DOWN at the ends
    for i in range(3, 7):
        add_waveguide(-i * pitch, w_thin, -dy)
        
    y_minus_7 = -(6 * pitch + w_thin/2 + g + W_thick/2)
    add_waveguide(y_minus_7, W_thick, -dy)

    # --- Apply Bounding Box Clipping ---
    
    # The image shows the thick top/bottom features having perfectly flat outer bounds
    # while gradually getting thinner towards the horizontal extremes.
    bbox = gf.components.rectangle(size=(L_total, total_height), layer=(1, 0), centered=True)
    
    # Intersect the continuous waveguide group with the 120x4 rectangle to form the clipped geometry bounds
    final_geometry = gf.boolean(A=wg_group, B=bbox, operation="and", layer=(1, 0))
    c << final_geometry

    return c

if __name__ == "__main__":
    # Generate the component and write it to a GDS file
    c = apodized_symmetric_coupler()
    c.write_gds("apodized_symmetric_coupler.gds")