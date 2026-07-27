import gdsfactory as gf
import numpy as np

@gf.cell
def bend_s_circular(size: tuple[float, float], cross_section) -> gf.Component:
    """Creates an S-bend component composed of two circular arcs.

    This is a custom component to work around the incompatibility between
    the GDSFactory router and bend_circular.

    Args:
        size: A tuple (dx, dy) representing the horizontal and vertical
              displacement of the S-bend.
        cross_section: The waveguide cross-section.
    """
    c = gf.Component()
    dx, dy = size

    # Calculate the required radius and angle for two identical circular arcs
    # to form the S-bend shape.
    # R = (dx^2 + dy^2) / (4*dy)
    # cos(A) = 1 - dy / (2*R)
    if dy == 0: # Handle straight case
        c.add_ref(gf.components.straight(length=dx, cross_section=cross_section))
        c.add_port("o1", port=c.ports["o1"])
        c.add_port("o2", port=c.ports["o2"])
        return c
        
    radius = (dx**2 + dy**2) / (4 * dy)
    cos_angle = 1 - dy / (2 * radius)
    angle = np.rad2deg(np.arccos(cos_angle))

    # Create the two circular bends
    b1 = c << gf.components.bend_circular(
        radius=radius, angle=angle, cross_section=cross_section
    )
    b2 = c << gf.components.bend_circular(
        radius=radius, angle=angle, cross_section=cross_section
    )

    # Assemble the S-bend
    b2.mirror_y()
    b2.connect("o1", b1.ports["o2"])
    c.add_port("o1", port=b1.ports["o1"])
    c.add_port("o2", port=b2.ports["o2"])
    return c


@gf.cell
def create_directional_coupler_manual_assembly():
    """
    Generates the directional coupler by manually assembling a central straight
    section and four custom circular S-bends.
    """
    # --- 1. Define component parameters ---
    waveguide_width = 0.8
    coupling_gap = 0.25
    coupling_length = 40.0
    s_bend_dx = 40.0
    port_separation_dy = 3.2  # Center-to-center distance of I/O ports

    xs = gf.cross_section.cross_section(width=waveguide_width)

    # --- 2. Create the main component and add the central section ---
    c = gf.Component()
    core = c << gf.components.coupler_straight(
        length=coupling_length, gap=coupling_gap, cross_section=xs
    )

    # --- 3. Calculate the required size for the S-bends ---
    # Vertical distance between ports in the coupling section
    coupler_dy = waveguide_width + coupling_gap
    # Vertical displacement needed for each S-bend
    s_bend_dy = (port_separation_dy - coupler_dy) / 2
    s_bend_size = (s_bend_dx, s_bend_dy)

    # --- 4. Add and connect the four S-bends ---
    s_bend_tl = c << bend_s_circular(size=s_bend_size, cross_section=xs)
    s_bend_bl = c << bend_s_circular(size=s_bend_size, cross_section=xs)
    s_bend_tr = c << bend_s_circular(size=s_bend_size, cross_section=xs)
    s_bend_br = c << bend_s_circular(size=s_bend_size, cross_section=xs)

    # Connect left-side S-bends
    s_bend_tl.connect("o2", core.ports["o1"])
    s_bend_bl.mirror_y()
    s_bend_bl.connect("o2", core.ports["o2"])

    # Connect right-side S-bends
    s_bend_tr.connect("o1", core.ports["o4"])
    s_bend_br.mirror_y()
    s_bend_br.connect("o1", core.ports["o3"])
    
    # --- 5. Add the final component ports ---
    c.add_port("o1", port=s_bend_tl.ports["o1"])
    c.add_port("o2", port=s_bend_bl.ports["o1"])
    c.add_port("o3", port=s_bend_br.ports["o2"])
    c.add_port("o4", port=s_bend_tr.ports["o2"])

    return c

# This block ensures the code runs only when the script is executed directly.
if __name__ == "__main__":
    device = create_directional_coupler_manual_assembly()
    device.write_gds("output.gds")