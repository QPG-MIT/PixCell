import gdsfactory as gf

def create_component() -> gf.Component:
    """
    Recreates the tapered directional coupler geometry based on the provided
    image and footprint constraints using gdsfactory parametric primitives.

    The geometry is constructed by creating a central directional coupler
    and attaching four tapers to its ports, following the component
    assembly pattern.

    The parameters are derived from the total footprint of 120x4 um and
    a visual analysis of the component's features.
    """

    # --- 1. Define Parameters from Footprint and Image Analysis ---

    # Overall footprint dimensions from the task constraint
    footprint_x = 120.0
    footprint_y = 4.0

    # Define geometric parameters based on visual inspection and footprint
    # The tapers at the ends are clearly visible in the cropped images.
    taper_length = 10.0
    port_width = 1.0  # Assume the widest part of the taper at the port
    wg_width = 0.5  # Assume a standard waveguide width for the core
    gap = 0.2  # A reasonable assumption for the coupling gap

    # Derive vertical port separation (dy) from the total height
    # footprint_y = dy (center-to-center) + port_width
    dy = footprint_y - port_width

    # Derive the dimensions of the central coupler section
    # footprint_x = 2*taper_length + total_coupler_length
    total_coupler_length = footprint_x - 2 * taper_length  # Should be 100.0 um

    # Split the coupler's length into bend sections (dx) and a straight
    # coupling section (length). A 20/60/20 split is a reasonable design.
    coupler_dx = 20.0
    coupler_length = 60.0

    # Sanity check total length: 2*taper_length + 2*coupler_dx + coupler_length
    # 2*10 + 2*20 + 60 = 20 + 40 + 60 = 120.0. Matches footprint_x.
    # Sanity check total height: dy + port_width = 3.0 + 1.0 = 4.0. Matches footprint_y.

    # --- 2. Create the Component using the Assembly Pattern ---

    # Create a new, empty component to hold the final device
    c = gf.Component("tapered_directional_coupler")

    # Define the cross-section for the core waveguides
    xs = gf.cross_section.cross_section(width=wg_width)

    # Create the central coupler primitive
    # This component parametrically creates the S-bends and the straight section.
    coupler_core = gf.components.coupler(
        length=coupler_length,
        gap=gap,
        dy=dy,
        dx=coupler_dx,
        cross_section=xs,
    )

    # Create the taper primitive that will be used for all four ports
    taper = gf.components.taper(
        length=taper_length, width1=wg_width, width2=port_width
    )

    # --- 3. Assemble the Primitives ---

    # Add the central coupler as a reference in the main component
    coupler_ref = c << coupler_core

    # Create and place the four tapers by connecting them to the coupler's ports
    # Coupler port naming: o1=BottomLeft, o2=TopLeft, o3=TopRight, o4=BottomRight
    # Taper port naming: o1=narrow end, o2=wide end

    # Input tapers (must be mirrored to face left)
    taper_in_bot = c << taper
    taper_in_top = c << taper
    taper_in_bot.mirror()  # Mirror horizontally
    taper_in_top.mirror()

    # After mirroring, port 'o1' is on the right (narrow) and 'o2' is on the left (wide)
    taper_in_bot.connect("o1", coupler_ref.ports["o1"])
    taper_in_top.connect("o1", coupler_ref.ports["o2"])

    # Output tapers (no mirroring needed)
    taper_out_top = c << taper
    taper_out_bot = c << taper

    taper_out_top.connect("o1", coupler_ref.ports["o3"])
    taper_out_bot.connect("o1", coupler_ref.ports["o4"])

    # --- 4. Expose the External Ports ---

    # The final component's ports are the wide ends of the tapers
    c.add_port("o1", port=taper_in_bot.ports["o2"])
    c.add_port("o2", port=taper_in_top.ports["o2"])
    c.add_port("o3", port=taper_out_top.ports["o2"])
    c.add_port("o4", port=taper_out_bot.ports["o2"])

    return c

# This block is the fix. It ensures the script is executable.
# When run, it calls the function defined above and saves the output.
if __name__ == "__main__":
    # Instantiate the component by calling the creation function
    my_component = create_component()
    
    # Write the component to a GDS file in the current directory
    my_component.write_gds("tapered_directional_coupler.gds")
    
    # You can also uncomment the line below to visualize the component
    # my_component.show()