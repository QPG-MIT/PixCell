import gdsfactory as gf
from gdsfactory.generic_tech import get_generic_pdk

# --- Activate the Generic PDK ---
pdk = get_generic_pdk()
pdk.activate()

@gf.cell
def inverse_taper_coupler():
    """
    Recreates the inverse taper edge coupler.
    
    Refinements:
    1. Compacted input dimensions (thinner wgs, smaller gap) to maximize vertical flare.
    2. Adjusted straight/bend ratio for a smoother curve profile.
    3. Taper length tuned to terminate exactly at the 3/4 mark (30um).
    """
    c = gf.Component()

    # --- Constraints ---
    total_length = 40.0
    total_height = 1.7

    # --- Geometric Parameters ---
    # THINNER dimensions to match the sleek look of the reference
    width_center_in = 0.4     # Reduced from 0.45
    width_center_tip = 0.05
    width_arm = 0.2           # Reduced from 0.25 to look less "heavy"
    
    # TIGHTER gap to contrast with the wide output
    gap_input = 0.1           # Reduced from 0.15

    # Longitudinal Dimensions
    # A 21/19 split allows the bend to be smoother while keeping the parallel section distinct
    len_straight = 21.0       
    len_bend = total_length - len_straight  # 19.0um
    
    # Taper ends at 3/4 of the total length, creating the distinct "fork" appearance
    len_taper = 30.0          

    # --- Vertical Calculations ---
    
    # 1. Output Position (Right Side)
    # Arms pushed to the absolute edge of the 1.7um footprint
    y_top_edge = total_height / 2
    y_arm_out_center = y_top_edge - (width_arm / 2)

    # 2. Input Position (Left Side)
    # Highly compacted cluster
    # y = (Center_WG/2) + Gap + (Arm_WG/2)
    y_arm_in_center = (width_center_in / 2) + gap_input + (width_arm / 2)

    # 3. S-Bend Shift
    # The tighter input results in a larger 'dy', creating a more pronounced curve
    dy = y_arm_out_center - y_arm_in_center

    # --- Geometry Creation ---

    # 1. Central Taper
    taper = c << gf.components.taper(
        length=len_taper,
        width1=width_center_in,
        width2=width_center_tip,
        layer=(1, 0)
    )

    # Cross-section for outer arms
    xs_arm = gf.cross_section.cross_section(width=width_arm, layer=(1, 0))

    # 2. Top Arm Construction
    t_straight = c << gf.components.straight(
        length=len_straight, 
        cross_section=xs_arm
    )
    t_bend = c << gf.components.bend_s(
        size=(len_bend, dy), 
        cross_section=xs_arm
    )
    
    # Assemble Top Arm
    t_straight.move((0, y_arm_in_center))
    t_bend.connect("o1", t_straight.ports["o2"])

    # 3. Bottom Arm Construction
    b_straight = c << gf.components.straight(
        length=len_straight, 
        cross_section=xs_arm
    )
    b_bend = c << gf.components.bend_s(
        size=(len_bend, -dy), 
        cross_section=xs_arm
    )
    
    # Assemble Bottom Arm
    b_straight.move((0, -y_arm_in_center))
    b_bend.connect("o1", b_straight.ports["o2"])

    # --- Ports ---
    c.add_port("o1", port=taper.ports["o1"])
    c.add_port("o2_top", port=t_bend.ports["o2"])
    c.add_port("o2_bot", port=b_bend.ports["o2"])

    return c

if __name__ == "__main__":
    device = inverse_taper_coupler()
    device.write_gds("inverse_taper_final_v3.gds")
    
    print("GDS saved: inverse_taper_final_v3.gds")
    try:
        device.show()
    except Exception:
        pass