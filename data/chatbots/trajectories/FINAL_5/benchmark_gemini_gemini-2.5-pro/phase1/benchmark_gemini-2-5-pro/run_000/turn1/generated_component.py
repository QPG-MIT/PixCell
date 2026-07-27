import gdsfactory as gf

@gf.cell
def create_bragg_coupler():
    """Creates the dual U-shaped Bragg grating structure."""

    # --------------------------------------------------------------------------
    # 1. Define Device Parameters from Footprint and Image Analysis
    # --------------------------------------------------------------------------
    footprint_w = 18.24
    footprint_h = 0.7

    wg_width = 0.1
    bend_radius = 0.1  # Radius to the center of the waveguide
    taper_len = 0.5
    center_line_width = 0.05
    gap_to_center_line = 0.025
    
    # Calculate straight section length to match the total width
    # Total width = taper_len + wg_len + (bend_radius + wg_width / 2)
    wg_len = footprint_w - taper_len - (bend_radius + wg_width / 2)

    # Grating parameters
    grating_len = 17.0
    grating_period = 0.3
    grating_duty_cycle = 0.5
    
    layer = (1, 0)
    
    # **FIX:** Use the gf.cross_section.cross_section() factory function to define 
    # the cross-section. The CrossSection class constructor does not directly 
    # accept 'width' and 'layer' arguments.
    xs = gf.cross_section.cross_section(width=wg_width, layer=layer)


    # --------------------------------------------------------------------------
    # 2. Create the Top U-shaped Grating Structure
    #    This is done by subtracting a grating from a solid U-shape.
    # --------------------------------------------------------------------------
    
    # Create a component for the solid body (Object A for boolean)
    c_solid = gf.Component("SolidUshape")
    
    # Add and connect the primitives to form the U-shape with a taper
    straight_outer = c_solid << gf.components.straight(
        length=wg_len, cross_section=xs
    )
    taper = c_solid << gf.components.taper(
        length=taper_len, width1=wg_width, width2=1e-9, layer=layer
    )
    bend = c_solid << gf.components.bend_circular(
        radius=bend_radius, angle=180, cross_section=xs
    )
    straight_inner = c_solid << gf.components.straight(
        length=wg_len, cross_section=xs
    )
    
    taper.connect("o2", straight_outer.ports["o1"])
    bend.connect("o1", straight_outer.ports["o2"])
    straight_inner.connect("o1", bend.ports["o2"])

    # Create a component for the grating trenches (Object B for boolean)
    c_grating = gf.Component("GratingTrenches")
    trench_width = grating_period * grating_duty_cycle
    trench_height = wg_width * 1.2  # Slightly larger to ensure clean subtraction
    num_periods = int(grating_len / grating_period)
    
    trench = gf.components.rectangle(size=(trench_width, trench_height), layer=layer)
    grating_array = c_grating.add_array(
        component=trench, columns=num_periods, rows=1, spacing=(grating_period, 0)
    )
    # Position the grating array to align with the inner straight waveguide
    grating_array.center = straight_inner.center

    # Perform the boolean operation to create the final U-shaped structure
    # This needs to be in its own cell for the final assembly
    @gf.cell
    def top_half_cell():
        c = gf.Component()
        _ = c << gf.boolean(A=c_solid, B=c_grating, operation="not", layer=layer)
        return c

    top_half = top_half_cell()


    # --------------------------------------------------------------------------
    # 3. Assemble the Full Device
    # --------------------------------------------------------------------------
    c_final = gf.Component("FinalDevice")

    # Add the top half and its mirrored version for the bottom
    ref_top = c_final << top_half
    ref_bottom = c_final << top_half.ref(mirror=True) # Vertical mirror

    # Add the central straight line
    center_line = c_final << gf.components.rectangle(
        size=(footprint_w, center_line_width), layer=layer, centered=True
    )
    
    # Position all components vertically to match the 0.7 um total height
    y_shift = (top_half.ysize / 2) + gap_to_center_line + (center_line_width / 2)

    ref_top.y += y_shift
    ref_bottom.y -= y_shift
    
    # Horizontally align the central line with the U-structures
    center_line.x = ref_top.x

    # Center the final device at (0, 0)
    c_final.move(origin=c_final.center, destination=(0,0))
    
    return c_final

# Instantiate the component
device = create_bragg_coupler()
device.show()