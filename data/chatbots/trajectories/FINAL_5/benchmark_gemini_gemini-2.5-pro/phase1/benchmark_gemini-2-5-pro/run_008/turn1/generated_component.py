import gdsfactory as gf
from gdsfactory.component import Component

@gf.cell
def grated_waveguide(
    length: float = 10.0,
    width: float = 0.5,
    period: float = 0.3,
    duty_cycle: float = 0.5,
    notch_depth: float = 0.25,
    notch_side: str = "bottom",
    layer: gf.typings.LayerSpec = (1, 0),
) -> Component:
    """Creates a straight waveguide with periodic notches on one side using a
    boolean operation. Replaces add_array with a loop for compatibility.

    Args:
        length: The length of the waveguide.
        width: The width of the waveguide.
        period: The period of the grating notches.
        duty_cycle: The duty cycle of the grating.
        notch_depth: The depth of the notches.
        notch_side: The side for the notches ('top' or 'bottom').
        layer: The GDS layer for the component.
    """
    # Component A for the boolean operation: the main waveguide body.
    waveguide_body = gf.components.rectangle(size=(length, width), layer=layer)

    # Component B for the boolean operation: a collection of notches to subtract.
    notches_collection = gf.Component()
    notch_width = period * (1 - duty_cycle)
    num_notches = int(length / period)
    notch = gf.components.rectangle(size=(notch_width, notch_depth), layer=layer)

    array_total_width = (num_notches - 1) * period + notch_width
    x_start = (length - array_total_width) / 2

    if notch_side == "bottom":
        y_pos = 0
    elif notch_side == "top":
        y_pos = width - notch_depth
    else:
        raise ValueError("notch_side must be 'top' or 'bottom'")

    for i in range(num_notches):
        notch_ref = notches_collection << notch
        notch_ref.origin = (x_start + i * period, y_pos)

    c_final = gf.boolean(waveguide_body, notches_collection, operation="not", layer=layer)

    c_final.add_port("o1", center=(0, width / 2), width=width, orientation=180, layer=layer)
    c_final.add_port("o2", center=(length, width / 2), width=width, orientation=0, layer=layer)
    c_final.auto_rename_ports()
    return c_final


@gf.cell
def create_arm(
    width: float = 0.15,
    layer: gf.typings.LayerSpec = (1, 0),
    length_grating: float = 4.89,
    length_straight_end: float = 4.89,
    taper_length: float = 2.0,
    bend_u_radius: float = 1.5,
    bend_out_radius: float = 4.0,
    bend_out_angle: float = -60.0,
    notch_side: str = "bottom",
) -> Component:
    """Assembles one of the U-shaped arms with a grating."""
    c = Component()
    
    # FIX: The error is caused by the default min_bend_radius (10.0) being
    # larger than the desired bend_u_radius (1.5). We set radius_min=None
    # to disable this design rule check for this specific cross-section.
    xs = gf.cross_section.cross_section(width=width, layer=layer, radius_min=None)

    # Create all the sub-components
    grated_wg = c << grated_waveguide(
        length=length_grating,
        width=width,
        period=0.3,
        duty_cycle=0.5,
        notch_depth=width / 2,
        notch_side=notch_side,
        layer=layer,
    )
    bend_u = c << gf.components.bend_euler(radius=bend_u_radius, angle=180, cross_section=xs)
    straight_end = c << gf.components.straight(length=length_straight_end, cross_section=xs)
    taper_end = c << gf.components.taper(
        length=taper_length, width1=width, width2=0.01, layer=layer
    )
    bend_out = c << gf.components.bend_euler(radius=bend_out_radius, angle=bend_out_angle, cross_section=xs)

    # Connect the components in sequence, starting from the central grating section
    bend_out.connect("o1", grated_wg.ports["o2"])
    bend_u.connect("o1", grated_wg.ports["o1"])
    straight_end.connect("o1", bend_u.ports["o2"])
    taper_end.connect("o1", straight_end.ports["o2"])

    # Add ports to the composite arm component
    c.add_port("tip", port=taper_end.ports["o2"])
    c.add_port("out", port=bend_out.ports["o2"])
    return c


@gf.cell
def grated_directional_coupler() -> Component:
    """Creates the full dual-arm grated directional coupler device."""
    c = Component()
    
    # Parameters derived from footprint and image analysis
    bus_width = 0.2
    arm_width = 0.15
    gap = 0.1
    layer = (1, 0)
    
    length_straight_sections = 4.89
    
    dummy_arm = create_arm(width=arm_width, layer=layer, length_grating=length_straight_sections, length_straight_end=length_straight_sections)
    bus_length = dummy_arm.xsize + 2.0
    bus_xs = gf.cross_section.cross_section(width=bus_width, layer=layer)
    bus = c << gf.components.straight(length=bus_length, cross_section=bus_xs)
    bus.move(origin=bus.center, destination=(0, 0))

    # Create and position the top arm
    arm_top = c << create_arm(
        width=arm_width, layer=layer, notch_side="bottom",
        length_grating=length_straight_sections,
        length_straight_end=length_straight_sections
    )
    arm_top.xmin = bus.xmin + 1.0
    arm_top.y = bus.y + gap + bus_width / 2 + arm_width / 2

    # Create and position the bottom arm
    arm_bottom = c << create_arm(
        width=arm_width, layer=layer, notch_side="top",
        length_grating=length_straight_sections,
        length_straight_end=length_straight_sections
    )
    arm_bottom.xmin = bus.xmin + 1.0
    arm_bottom.y = bus.y - gap - bus_width / 2 - arm_width / 2

    # Add ports to the final device
    c.add_port("o1", port=bus.ports["o1"])
    c.add_port("o2", port=bus.ports["o2"])
    c.add_port("o3", port=arm_top.ports["out"])
    c.add_port("o4", port=arm_bottom.ports["out"])
    
    return c

# Main execution block to generate and display the GDS
if __name__ == "__main__":
    device = grated_directional_coupler()
    device.show()