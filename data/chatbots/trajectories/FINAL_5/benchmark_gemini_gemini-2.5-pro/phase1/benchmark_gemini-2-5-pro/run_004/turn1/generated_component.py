import gdsfactory as gf
from gdsfactory.typings import CrossSectionSpec

@gf.cell
def bragg_grating(
    length: float = 10.0,
    period: float = 0.3,
    duty_cycle: float = 0.5,
    cross_section: CrossSectionSpec = "strip",
) -> gf.Component:
    """Creates a Bragg grating by etching trenches into a straight waveguide.

    This component is built using rectangle primitives and a boolean operation.

    Args:
        length: Approximate total length of the grating.
        period: Period of the grating.
        duty_cycle: Duty cycle of the grating (waveguide material portion).
        cross_section: The cross-section of the waveguide.

    Returns:
        A Component containing the Bragg grating.
    """
    c = gf.Component()
    xs = gf.get_cross_section(cross_section)
    width = xs.width
    layer = xs.layer

    n_periods = int(length / period)
    actual_length = n_periods * period

    # Main waveguide body
    wg = gf.components.rectangle(size=(actual_length, width), layer=layer)

    # Create trenches for subtraction on a temporary layer
    trench_width = period * (1 - duty_cycle)
    trench = gf.components.rectangle(size=(trench_width, width), layer=(99, 0))

    # Create an array of trenches to form the etching pattern
    trenches = gf.Component()
    trenches.add_array(
        trench,
        columns=n_periods,
        rows=1,
        spacing=(period, 0),
        origin=((period * duty_cycle) / 2, 0),
    )

    # Boolean 'not' operation to subtract trenches from the waveguide
    final_shape = gf.boolean(A=wg, B=trenches, operation="not", layer=layer)

    # Add the final geometry to the component and define ports
    ref = c << final_shape
    c.add_port("o1", center=(0, 0), orientation=180, cross_section=xs)
    c.add_port("o2", center=(actual_length, 0), orientation=0, cross_section=xs)
    c.info["length"] = actual_length
    return c


@gf.cell
def create_photonic_device() -> gf.Component:
    """
    Recreates the device from the provided image using GDSFactory,
    adhering to the specified footprint of [18.24, 0.7] um.

    The device is a contra-directional coupler with two outer U-shaped
    waveguides featuring Bragg gratings, coupled to a central bus waveguide.
    """
    # --- 1. Define Core Parameters ---
    wg_width = 0.1
    gap = 0.05
    u_bend_radius = 0.15
    taper_len = 1.0
    out_bend_radius = 2.2
    out_bend_angle = -45
    grating_period = 0.3
    grating_duty_cycle = 0.5

    # --- 2. Define Custom Cross-Section FIRST to allow small bend radius ---
    # This is the critical fix. This object must be created before any small bends.
    xs_custom = gf.cross_section.cross_section(
        width=wg_width, layer=(1, 0), radius_min=0.1
    )

    # --- 3. Calculate dependent lengths using the custom cross-section ---
    # FIX: Pass xs_custom to the bend_euler calls used for info gathering.
    bend180_for_info = gf.components.bend_euler(radius=u_bend_radius, angle=180, p=0.5, cross_section=xs_custom)
    bend_out_for_info = gf.components.bend_euler(radius=out_bend_radius, angle=abs(out_bend_angle), cross_section=xs_custom)
    
    left_arm_span = taper_len + bend180_for_info.info["width"]
    right_arm_span = bend_out_for_info.info["width"]
    grating_len = 18.24 - left_arm_span - right_arm_span

    # --- 4. Arm Sub-Component Assembly ---
    top_arm = gf.Component("top_arm")

    grating_wg = bragg_grating(
        length=grating_len,
        period=grating_period,
        duty_cycle=grating_duty_cycle,
        cross_section=xs_custom,
    )
    bend180 = bend180_for_info  # Reuse the component already created
    taper = gf.components.taper(length=taper_len, width1=wg_width, width2=1e-3, cross_section=xs_custom)
    bend_out = gf.components.bend_euler(radius=out_bend_radius, angle=out_bend_angle, cross_section=xs_custom)

    # Connect the primitives to form the top arm
    g_ref = top_arm << grating_wg
    b180_ref = top_arm << bend180
    t_ref = top_arm << taper
    bout_ref = top_arm << bend_out

    b180_ref.connect("o2", g_ref.ports["o1"])
    t_ref.connect("o1", b180_ref.ports["o1"])
    bout_ref.connect("o1", g_ref.ports["o2"])

    # --- 5. Full Device Assembly ---
    device = gf.Component()
    y_offset = (wg_width / 2) + gap + (wg_width / 2)
    
    top_ref = device << top_arm
    top_ref.y = y_offset
    
    bus_length = g_ref.info['length'] + 2.0
    bus = gf.components.straight(length=bus_length, cross_section=xs_custom)
    bus_ref = device << bus
    bus_ref.center = (top_ref.x + g_ref.x + g_ref.info['length']/2, 0)

    bottom_ref = device << top_arm
    bottom_ref.mirror()
    bottom_ref.x = top_ref.x
    bottom_ref.y = -y_offset
    
    device.center = (0, 0)
    
    return device

# Create and display the component
final_device = create_photonic_device()
# final_device.show() # Uncomment to display in KLayout
# final_device.write_gds("photonic_device.gds") # Uncomment to save the GDS file

# Verify the footprint of the generated device
print(f"Generated device footprint (width, height): {final_device.size}")