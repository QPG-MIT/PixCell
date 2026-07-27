import gdsfactory as gf
from gdsfactory.typings import CrossSectionSpec

@gf.cell
def my_coupler_like_device(
    wg_width: float = 0.5,
    gap_coupler: float = 0.2,  # Gap between inner edges in the central coupling section
    length_straight_in: float = 15.0,  # Length of input/output straight sections
    length_coupler: float = 70.0,  # Length of the central parallel coupling section
    cross_section: CrossSectionSpec = "strip",
) -> gf.Component:
    """
    Recreates the directional coupler-like geometry from the provided image.

    The device consists of two parallel waveguides that transition from a wider
    vertical separation at the inputs/outputs to a narrower separation in the center
    through S-bends.

    Args:
        wg_width: The width of the waveguides.
        gap_coupler: The gap between the inner edges of the waveguides
                      in the central parallel region.
        length_straight_in: The length of the straight sections at the input and output.
        length_coupler: The length of the straight parallel section in the middle.
        cross_section: The cross-section specification for the waveguides.

    Returns:
        A gdsfactory Component representing the device.
    """
    c = gf.Component("coupler_like_device")
    xs = gf.get_cross_section(cross_section, width=wg_width)

    # --- Define overall device dimensions based on footprint [120, 4] ---
    total_length = 120.0
    total_height = 4.0

    # Calculate vertical offset for input/output port centers from device centerline (y=0)
    # The total height (4um) covers the outermost edges of the waveguides.
    # So, the center-to-center vertical separation of input/output waveguides is total_height - wg_width.
    y_port_offset = (total_height - wg_width) / 2  # = (4 - 0.5) / 2 = 1.75 um

    # Calculate vertical offset for waveguide centers in the coupling region from device centerline (y=0)
    # Center-to-center separation in coupling region = wg_width + gap_coupler.
    y_coupler_offset = (wg_width + gap_coupler) / 2  # = (0.5 + 0.2) / 2 = 0.35 um

    # Calculate horizontal displacement (dx) for each S-bend
    # total_length = 2 * length_straight_in + length_coupler + 2 * dx_s_bend
    dx_s_bend = (total_length - (2 * length_straight_in) - length_coupler) / 2

    if dx_s_bend < 0:
        raise ValueError(
            f"Invalid lengths: (2 * length_straight_in) ({2*length_straight_in:.1f}um) "
            f"+ length_coupler ({length_coupler:.1f}um) "
            f"exceeds total_length ({total_length:.1f}um). "
            f"dx_s_bend calculated as {dx_s_bend:.1f}um. Please adjust lengths."
        )
    if dx_s_bend == 0:
        print("Warning: dx_s_bend is 0, S-bends will be vertical lines. Consider adjusting lengths.")

    # Vertical displacement (dy) for each S-bend
    dy_s_bend = y_port_offset - y_coupler_offset  # = 1.75 - 0.35 = 1.4 um

    # --- Define primitive components ---
    straight_io = gf.components.straight(length=length_straight_in, cross_section=xs)
    straight_coupler_segment = gf.components.straight(length=length_coupler, cross_section=xs)

    # S-bends definitions:
    # bend_s(size=(dx, dy)) has port 'o1' at (0,0) and port 'o2' at (dx, dy).
    # For top path (y decreasing towards center): needs a bend that ends at lower Y. So dy is negative.
    bend_s_down = gf.components.bend_s(size=(dx_s_bend, -dy_s_bend), cross_section=xs)
    # For bottom path (y increasing towards center): needs a bend that ends at higher Y. So dy is positive.
    bend_s_up = gf.components.bend_s(size=(dx_s_bend, dy_s_bend), cross_section=xs)


    # --- Construct Top Waveguide Path ---
    # 1. Central straight coupling segment (top)
    s_coupler_top = c << straight_coupler_segment
    s_coupler_top.movey(y_coupler_offset)
    # Position it horizontally so its center aligns with the component's center
    s_coupler_top.movex(total_length / 2 - length_coupler / 2)

    # 2. Left S-bend (connects input straight to s_coupler_top)
    # The 'o2' port of bend_s_down is at (dx, -dy) relative to its 'o1' port.
    # Connecting its 'o2' to s_coupler_top.ports["o1"] means its 'o1' will be at
    # the correct higher Y position for the input.
    sb_left_top = c << bend_s_down
    sb_left_top.connect("o2", s_coupler_top.ports["o1"])

    # 3. Input straight (top)
    s_in_top = c << straight_io
    s_in_top.connect("o2", sb_left_top.ports["o1"])

    # 4. Right S-bend (connects s_coupler_top to output straight)
    # The 'o2' port of bend_s_up is at (dx, dy) relative to its 'o1' port.
    # Connecting its 'o1' to s_coupler_top.ports["o2"] means its 'o2' will be at
    # the correct higher Y position for the output.
    sb_right_top = c << bend_s_up
    sb_right_top.connect("o1", s_coupler_top.ports["o2"])

    # 5. Output straight (top)
    s_out_top = c << straight_io
    s_out_top.connect("o1", sb_right_top.ports["o2"])

    # --- Construct Bottom Waveguide Path (mirror image of top) ---
    # 1. Central straight coupling segment (bottom)
    s_coupler_bottom = c << straight_coupler_segment
    s_coupler_bottom.movey(-y_coupler_offset)
    s_coupler_bottom.movex(total_length / 2 - length_coupler / 2)

    # 2. Left S-bend (connects input straight to s_coupler_bottom)
    # This bend needs to go upwards (from lower Y at input to higher Y at coupler)
    # So, use bend_s_up and connect its 'o2' (higher Y) to s_coupler_bottom.ports["o1"].
    sb_left_bottom = c << bend_s_up
    sb_left_bottom.connect("o2", s_coupler_bottom.ports["o1"])

    # 3. Input straight (bottom)
    s_in_bottom = c << straight_io
    s_in_bottom.connect("o2", sb_left_bottom.ports["o1"])

    # 4. Right S-bend (connects s_coupler_bottom to output straight)
    # This bend needs to go downwards (from higher Y at coupler to lower Y at output)
    # So, use bend_s_down and connect its 'o1' (higher Y) to s_coupler_bottom.ports["o2"].
    sb_right_bottom = c << bend_s_down
    sb_right_bottom.connect("o1", s_coupler_bottom.ports["o2"])

    # 5. Output straight (bottom)
    s_out_bottom = c << straight_io
    s_out_bottom.connect("o1", sb_right_bottom.ports["o2"])

    # --- Expose Ports ---
    # Ports are defined at the extremities of the component.
    # The component is implicitly centered on x-axis by the positioning of s_coupler_top/bottom.
    # The left-most x-coordinate is 0, right-most is 120.
    # The bottom-most y-coordinate is -2, top-most is 2.
    c.add_port("o1", port=s_in_top.ports["o1"])    # Top-left input
    c.add_port("o2", port=s_in_bottom.ports["o1"]) # Bottom-left input
    c.add_port("o3", port=s_out_top.ports["o2"])   # Top-right output
    c.add_port("o4", port=s_out_bottom.ports["o2"])# Bottom-right output

    return c

# --- Create and Save the Device ---
if __name__ == "__main__":
    # Parameters chosen to fit the 120x4um footprint and resemble the image
    # dx_s_bend calculation: (120 - 2*15 - 70) / 2 = (120 - 30 - 70) / 2 = 20 / 2 = 10 um
    # dy_s_bend calculation: 1.75 - 0.35 = 1.4 um
    # So, each S-bend is (10um, 1.4um)
    device = my_coupler_like_device(
        wg_width=0.5,
        gap_coupler=0.2,
        length_straight_in=15.0,
        length_coupler=70.0,
        cross_section="strip",
    )

    device.show() # Opens the component in KLayout if installed
    device.write_gds("my_coupler_like_device.gds") # Uncommented to save the GDS file