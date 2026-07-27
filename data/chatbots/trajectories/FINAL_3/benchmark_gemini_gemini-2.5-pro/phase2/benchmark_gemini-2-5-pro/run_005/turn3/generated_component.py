import gdsfactory as gf
import pathlib
import numpy as np

@gf.cell
def tapered_s_bend(
    size: tuple[float, float] = (15.0, 4.0),
    width_start: float = 1.0,
    width_middle: float = 0.4,
    npoints: int = 101,
) -> gf.Component:
    """
    Creates a single S-bend component with a parabolic width taper.
    The width is `width_start` at the ends and `width_middle` at the center.

    This is achieved by splitting the S-bend path into two halves and
    extruding each half with a `gf.path.transition`.

    Args:
        size: A tuple (dx, dy) for the size of the S-bend.
        width_start: The width of the waveguide at its input and output ports.
        width_middle: The minimum width of the waveguide at its center point.
        npoints: The number of points used to define the S-bend's Bezier curve.
    """
    c = gf.Component()

    # 1. Define the start and middle cross-sections
    xs_start = gf.cross_section.cross_section(width=width_start)
    xs_middle = gf.cross_section.cross_section(width=width_middle)

    # 2. Define the two transitions: start->middle and middle->start
    # The 'parabolic' width_type ensures a smooth, non-linear taper.
    t_start_to_middle = gf.path.transition(
        cross_section1=xs_start, cross_section2=xs_middle, width_type="parabolic"
    )
    t_middle_to_start = gf.path.transition(
        cross_section1=xs_middle, cross_section2=xs_start, width_type="parabolic"
    )

    # 3. Get the full S-bend path from the standard component's Bezier curve calculation
    # We create a temporary component just to extract its calculated path.
    s_bend_dummy = gf.components.bend_s(size=size, npoints=npoints)
    s_bend_path = s_bend_dummy.info["path"]
    
    # 4. Split the path into two halves at the midpoint
    points = s_bend_path.points
    mid_point_index = npoints // 2
    
    path1_pts = points[: mid_point_index + 1] # First half, including midpoint
    path2_pts = points[mid_point_index:]      # Second half, starting from midpoint

    path1 = gf.Path(path1_pts)
    path2 = gf.Path(path2_pts)

    # 5. Extrude each path half with its corresponding transition
    half1 = gf.path.extrude_transition(path=path1, transition=t_start_to_middle)
    half2 = gf.path.extrude_transition(path=path2, transition=t_middle_to_start)

    # 6. Combine the two halves into the final component
    ref1 = c << half1
    ref2 = c << half2
    ref2.connect("o1", ref1.ports["o2"])

    c.add_port("o1", port=ref1.ports["o1"])
    c.add_port("o2", port=ref2.ports["o2"])

    return c

@gf.cell
def create_crossing_coupler():
    """
    Creates a device resembling the target image, featuring:
    - A true waveguide crossover on the left, created with a boolean union.
    - A flared waveguide section on the right.
    - Waveguides with a parabolic taper, created using the `tapered_s_bend` cell.
    """
    c = gf.Component("crossing_coupler")

    # --- 1. Define Parameters ---
    port_sep = 8.0
    center_sep = 1.4
    bend_length_x = 15.0
    width_at_ports = 1.0
    width_at_center = 0.4

    # --- 2. Create the Tapered S-Bend Building Blocks using the new function ---
    # For the right-side flare (top half):
    dy_flare = (port_sep - center_sep) / 2
    s_bend_flare = tapered_s_bend(
        size=(bend_length_x, dy_flare),
        width_start=width_at_ports,
        width_middle=width_at_center,
    )

    # For the left-side crossing (covers the full vertical span):
    dy_cross = (port_sep + center_sep) / 2
    s_bend_cross = tapered_s_bend(
        size=(bend_length_x, dy_cross),
        width_start=width_at_ports,
        width_middle=width_at_center,
    )
    
    # --- 3. Assemble the Component ---
    # A. Right Side (Flare)
    flare_top = c << s_bend_flare
    flare_bot = c << s_bend_flare.mirror_y()
    flare_top.movey(center_sep / 2)
    flare_bot.movey(-center_sep / 2)

    # B. Left Side (Crossing)
    cross_top_path = s_bend_cross.mirror()
    cross_top_path.movey(-center_sep / 2)
    
    cross_bot_path = s_bend_cross.mirror().mirror_y()
    cross_bot_path.movey(center_sep / 2)
    
    port_o1 = cross_top_path.ports["o2"].copy()
    port_o2 = cross_bot_path.ports["o2"].copy()
    
    crossing_shape = gf.boolean(cross_top_path, cross_bot_path, operation="or")
    c << crossing_shape
    
    # --- 4. Add Ports to the Final Component ---
    c.add_port(name="o1", port=port_o1)
    c.add_port(name="o2", port=port_o2)
    c.add_port(name="o3", port=flare_top.ports["o2"])
    c.add_port(name="o4", port=flare_bot.ports["o2"])
    
    return c

if __name__ == "__main__":
    device = create_crossing_coupler()
    
    # Optional: Display the component in the KLayout viewer for verification
    # device.show()
    
    # Save the component to a GDS file
    output_filename = "crossing_coupler.gds"
    device.write_gds(output_filename)
    
    print(f"Successfully generated GDS file: {pathlib.Path(output_filename).resolve()}")