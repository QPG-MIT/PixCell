import gdsfactory as gf
from gdsfactory.component import Component

# It is good practice to create a separate cell for a building block
# that will be used multiple times.
@gf.cell
def create_arm(
    width: float = 0.1,
    taper_length: float = 2.0,
    straight_length: float = 16.24,
    bend_radius: float = 0.075,
    grating_length: float = 10.0,
    spine_width: float = 0.08,
    tooth_width: float = 0.1,
    tooth_protrusion: float = 0.05,
    pitch: float = 0.2,
) -> Component:
    """Creates one of the U-shaped arms with an internal grating.

    The parameters are chosen to be compatible with a very small total height.
    """
    c = gf.Component()

    # --- FIX STARTS HERE ---
    # The requested bend_radius (0.075) is smaller than the GDSFactory default
    # minimum of 5.0. To bypass this design rule check (DRC), we create a
    # custom cross_section and set its `radius_min` to a very small value.
    xs_custom_bend = gf.cross_section.cross_section(width=width, radius_min=0.01)
    # --- FIX ENDS HERE ---

    # 1. Create the component parts that form the main waveguide path
    taper_tip = gf.components.taper(length=taper_length, width1=0.01, width2=width)
    straight_upper = gf.components.straight(length=straight_length, width=width)
    
    # Pass the custom cross_section to the bend_euler component to allow the small radius.
    bend_u = gf.components.bend_euler(radius=bend_radius, angle=-180, cross_section=xs_custom_bend)
    
    straight_lower_spine = gf.components.straight(
        length=grating_length, width=spine_width
    )

    # 2. Add parts as references to the component canvas
    ref_taper = c << taper_tip
    ref_straight_upper = c << straight_upper
    ref_bend = c << bend_u
    ref_spine = c << straight_lower_spine

    # 3. Connect the parts sequentially to form the continuous waveguide path
    ref_straight_upper.connect("o1", ref_taper.ports["o2"])
    ref_bend.connect("o1", ref_straight_upper.ports["o2"])
    ref_spine.connect("o1", ref_bend.ports["o2"])

    # 4. Create and place the grating teeth
    num_teeth = int(grating_length / pitch)
    tooth = gf.components.rectangle(size=(tooth_width, tooth_protrusion))
    ref_teeth = c.add_array(
        component=tooth, columns=num_teeth, rows=1, spacing=(pitch, 0)
    )

    # 5. Align the teeth array with the lower spine.
    ref_teeth.ymin = ref_spine.ymax
    ref_teeth.xmax = ref_spine.xmax

    return c


@gf.cell
def recreated_device() -> Component:
    """
    Recreates the device from the image, adhering to the specified footprint.
    The geometric parameters are derived to fit the total footprint of [18.24, 0.7].
    """
    total_width = 18.24
    divider_width = 0.1
    vertical_gap = 0.05
    wg_width = 0.1
    bend_radius = 0.075
    taper_length = 2.0
    straight_length = total_width - taper_length
    grating_length = 10.0
    spine_width = 0.08
    tooth_width = 0.1
    tooth_protrusion = 0.05
    pitch = 0.2

    c = gf.Component()

    arm_unit = create_arm(
        width=wg_width,
        taper_length=taper_length,
        straight_length=straight_length,
        bend_radius=bend_radius,
        grating_length=grating_length,
        spine_width=spine_width,
        tooth_width=tooth_width,
        tooth_protrusion=tooth_protrusion,
        pitch=pitch,
    )

    top_arm = c << arm_unit
    bottom_arm = c << arm_unit
    bottom_arm.mirror()

    divider = c << gf.components.rectangle(size=(total_width, divider_width))
    divider.ymin = -divider_width / 2
    divider.xmin = 0

    top_arm_target_ymin = (divider_width / 2) + vertical_gap
    top_arm.movey(top_arm_target_ymin - top_arm.ymin)

    bottom_arm_target_ymax = -(divider_width / 2) - vertical_gap
    bottom_arm.movey(bottom_arm_target_ymax - bottom_arm.ymax)

    return c

# Create an instance of the device and write it to a GDS file.
device = recreated_device()
device.write_gds("recreated_device.gds")