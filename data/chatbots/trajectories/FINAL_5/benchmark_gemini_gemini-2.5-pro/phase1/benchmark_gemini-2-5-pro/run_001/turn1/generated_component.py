import gdsfactory as gf

@gf.cell
def create_bragg_grating(
    length: float = 10.0,
    period: float = 0.35,
    duty_cycle: float = 0.5,
    width: float = 0.2,
    layer: gf.typings.LayerSpec = (1, 0),
) -> gf.Component:
    """Creates a Bragg grating from primitive shapes using a boolean operation."""
    c = gf.Component()
    
    # 1. Create the main straight waveguide body (bottom-left corner at (0,0))
    wg_main = gf.components.rectangle(size=(length, width), layer=layer)

    # 2. Create the geometry for a single gap to be subtracted
    gap_width = period * (1 - duty_cycle)
    # Make the gap rectangle taller than the waveguide to ensure a clean cut
    gap_height = width * 1.2
    
    # FIX: Create the gap box already centered at its origin using centered=True.
    # This avoids modifying the component directly and resolves the "Cell is locked" error.
    gap_box = gf.components.rectangle(size=(gap_width, gap_height), layer=layer, centered=True)

    # 3. Create an array of these gaps
    num_periods = int(length / period)
    gap_array = c.add_array(
        component=gap_box, columns=num_periods, rows=1, spacing=(period, 0)
    )
    # Position the array to start after the first solid section
    gap_array.xmin = period * duty_cycle

    # 4. Perform the boolean subtraction
    grating = gf.boolean(A=wg_main, B=gap_array, operation="not", layer=layer)

    # 5. Add the resulting geometry and ports to the component
    c.add_polygon(grating.polygons, layer=layer)
    # Add ports centered on the waveguide's vertical axis
    c.add_port(
        name="o1", center=(0, width / 2), width=width, orientation=180, layer=layer
    )
    c.add_port(
        name="o2", center=(length, width / 2), width=width, orientation=0, layer=layer
    )
    c.info['length'] = length
    c.info['width'] = width
    return c

@gf.cell
def asymmetric_arm(
    wg_width: float = 0.2,
    grating_length: float = 15.83,
    grating_period: float = 0.35,
    grating_duty_cycle: float = 0.5,
    bend_radius: float = 1.0,
    taper_length: float = 4.0,
    curve_taper_radius: float = 2.0,
    curve_taper_angle: float = 45.0,
):
    """
    Creates one of the two vertically mirrored U-shaped arms.
    """
    c = gf.Component()
    xs = gf.cross_section.strip(width=wg_width)

    grating_arm = c << create_bragg_grating(
        length=grating_length,
        period=grating_period,
        duty_cycle=grating_duty_cycle,
        width=wg_width,
    )

    bend = c << gf.components.bend_euler(
        radius=bend_radius, angle=180, cross_section=xs
    )
    bend.connect("o1", grating_arm.ports["o2"])

    top_straight = c << gf.components.straight(
        length=grating_length - taper_length, cross_section=xs
    )
    top_taper = c << gf.components.taper(
        length=taper_length, width1=wg_width, width2=0.01, cross_section=xs
    )
    top_straight.connect("o1", bend.ports["o2"])
    top_taper.connect("o1", top_straight.ports["o2"])

    path = gf.path.arc(radius=curve_taper_radius, angle=-curve_taper_angle)
    transition = gf.path.transition(
        cross_section1=xs, cross_section2=gf.cross_section.strip(width=0.01)
    )
    curved_taper = c << gf.path.extrude_transition(path, transition)
    curved_taper.connect("o1", grating_arm.ports["o1"])

    return c

@gf.cell
def device():
    """
    Constructs the full device by assembling two mirrored arms
    and a central straight line.
    """
    c = gf.Component()

    # --- Define Device Parameters based on Footprint ---
    wg_width = 0.2
    gap = 0.1
    center_line_width = 0.1
    grating_len = 15.83
    bend_rad = 1.0
    taper_len = 4.0
    curve_rad = 2.0
    curve_angle = 45.0

    # --- Component Assembly ---
    arm_component = asymmetric_arm(
        wg_width=wg_width,
        grating_length=grating_len,
        grating_period=0.35, # Explicitly set grating period
        grating_duty_cycle=0.5, # Explicitly set duty cycle
        bend_radius=bend_rad,
        taper_length=taper_len,
        curve_taper_radius=curve_rad,
        curve_taper_angle=curve_angle,
    )

    top_arm_ref = c << arm_component
    bottom_arm_ref = c << arm_component
    bottom_arm_ref.mirror()

    # Correctly calculate the y-position for the arms.
    # The origin of the arm is at the bottom of the grating waveguide.
    # We want the gap between the inner edges to be (2*gap + center_line_width).
    y_position = gap + center_line_width / 2
    top_arm_ref.y = y_position
    bottom_arm_ref.y = -y_position

    # Add the central straight line
    bbox = c.bbox
    device_width = bbox[1][0] - bbox[0][0]
    # Create the rectangle centered and then position its center. This is more robust.
    center_line = c << gf.components.rectangle(
        size=(device_width, center_line_width),
        layer=arm_component.get_layers().pop(),
        centered=True,
    )
    # Position the line at the horizontal center of the arms and at y=0.
    center_line.x = bbox[0][0] + device_width / 2
    center_line.y = 0
    
    c.center()
    return c

recreated_device = device()
# recreated_device.show()