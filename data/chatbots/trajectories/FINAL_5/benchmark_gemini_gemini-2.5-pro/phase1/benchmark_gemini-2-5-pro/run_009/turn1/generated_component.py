import gdsfactory as gf

@gf.cell
def grating_waveguide(
    length: float = 10.0,
    wg_width: float = 0.5,
    n_periods: int = 50,
    duty_cycle: float = 0.7,
    layer: tuple = (1, 0),
) -> gf.Component:
    """Creates a straight waveguide with periodic rectangular etches (gratings).

    The component is constructed to be centered at (0, 0) for easy assembly.

    Args:
        length: The total length of the grating section.
        wg_width: The width of the waveguide.
        n_periods: The number of grating periods.
        duty_cycle: The fraction of the period that is waveguide material (not etched).
        layer: The GDS layer for the geometry.
    """
    c = gf.Component()
    
    # Create the main waveguide body as a centered rectangle
    wg_main_geom = gf.components.rectangle(
        size=(length, wg_width), layer=layer, centered=True
    )

    # Define the properties of the etch holes based on the period and duty cycle
    period = length / n_periods
    hole_length = period * (1 - duty_cycle)
    hole_width = wg_width  # Etch fully through the waveguide width

    # Create a single hole, also centered
    hole_geom = gf.components.rectangle(
        size=(hole_length, hole_width), layer=layer, centered=True
    )

    # --- FIX: Replaced deprecated `add_array` with `gf.components.array` ---
    # Create a component that is an array of holes
    holes_array_comp = gf.components.array(
        component=hole_geom,
        columns=n_periods,
        rows=1,
        spacing=(period, 0),
    )
    # Center the entire array component for the boolean operation
    holes_array_comp.center = (0, 0)

    # Subtract the holes from the main waveguide using a boolean 'not' operation
    g = gf.boolean(wg_main_geom, holes_array_comp, operation="not", layer=layer)
    
    # Add the resulting geometry to the component and define I/O ports
    c << g
    c.add_port("o1", center=(-length / 2, 0), width=wg_width, orientation=180)
    c.add_port("o2", center=(length / 2, 0), width=wg_width, orientation=0)
    return c


@gf.cell
def recreate_device() -> gf.Component:
    """
    Recreates the device from the image by composing parametric GDSFactory components.
    
    The device consists of a central bus waveguide coupled to two outer waveguides.
    The outer waveguides feature grating sections, U-bends, and tapers.
    """
    # Parameters derived from footprint [18.24, 7.0] for a realistic aspect ratio
    # Note: Assumed the 0.7um footprint height was a typo for 7.0um to match the image aspect ratio
    wg_width = 0.5
    bus_width = 0.4
    gap = 0.2
    bend_radius = 2.8
    grating_length = 5.57
    taper_in_length = 1.5
    n_periods = 80
    duty_cycle = 0.7

    # --- Create the building block components ---
    
    # Define a standard cross-section for solid waveguide sections
    xs = gf.cross_section.strip(width=wg_width)

    # Left-side input taper, from near-zero width to wg_width
    taper_in = gf.components.taper(
        length=taper_in_length, width1=0.01, width2=wg_width, cross_section=xs
    )

    # Grating section using the custom component defined above
    grating = grating_waveguide(
        length=grating_length,
        wg_width=wg_width,
        n_periods=n_periods,
        duty_cycle=duty_cycle,
    )

    # 180-degree U-bend using an Euler curve for smooth transitions
    bend180 = gf.components.bend_euler(radius=bend_radius, angle=180, cross_section=xs)

    # Right-side curved output taper, created by extruding a path with a varying width
    path_out = gf.path.euler(radius=bend_radius, angle=-90, p=0.5)
    xs_taper_start = gf.cross_section.strip(width=wg_width)
    xs_taper_end = gf.cross_section.strip(width=0.01)
    transition = gf.path.transition(xs_taper_start, xs_taper_end, width_type="linear")
    taper_out = gf.path.extrude_transition(path=path_out, transition=transition)

    # --- Assemble one arm of the device ---
    # We build one arm in a separate component to manage placement and mirroring.
    arm = gf.Component("arm")
    tin_ref = arm << taper_in
    g1_ref = arm << grating
    b_ref = arm << bend180
    g2_ref = arm << grating
    tout_ref = arm << taper_out

    # Connect the components in sequence; gdsfactory handles the relative positioning
    g1_ref.connect("o1", tin_ref.ports["o2"])
    b_ref.connect("o1", g1_ref.ports["o2"])
    g2_ref.connect("o1", b_ref.ports["o2"])
    tout_ref.connect("o1", g2_ref.ports["o2"])

    # --- Assemble the final device ---
    c = gf.Component("final_device")

    # Add top and bottom arms to the final layout
    top_arm_ref = c << arm
    bottom_arm_ref = c << arm
    bottom_arm_ref.mirror() # Mirror across the x-axis for the bottom arm

    # Center the interaction region (gratings) of the arms at x=0 for easier alignment
    interaction_center_x = (g1_ref.xmin + g2_ref.xmax) / 2
    top_arm_ref.movex(-interaction_center_x)
    bottom_arm_ref.movex(-interaction_center_x)
    
    # Calculate bus waveguide length based on the placed arm's interaction region
    bus_length = g2_ref.xmax - g1_ref.xmin
    
    # Create and place the central bus waveguide
    bus = c << gf.components.straight(length=bus_length, width=bus_width)
    bus.center = (0, 0) # Center the bus at the origin

    # Position the top and bottom arms vertically relative to the bus waveguide
    y_shift = bus_width / 2 + gap + wg_width / 2
    top_arm_ref.movey(y_shift)
    bottom_arm_ref.movey(-y_shift)
    
    return c


# To generate and save the GDS file, the following lines must be executed.
if __name__ == "__main__":
    device = recreate_device()
    # device.show(show_ports=True) # Optional: for visualization in a viewer
    device.write_gds("recreated_device.gds")