import gdsfactory as gf

@gf.cell
def directional_coupler_from_image():
    """
    Recreates the directional coupler geometry from the provided image
    using GDSFactory's parametric coupler component.

    The component's dimensions are derived from the footprint constraint [120, 4] um.
    - Total length = 120 um
    - Port-to-port vertical separation = 4 um

    The total length is composed of two S-bends and a central straight section.
    Assuming these three sections are of equal length for visual balance:
    - S-bend horizontal length (dx) = 120 / 3 = 40 um
    - Straight coupling length = 120 / 3 = 40 um
    """
    c = gf.Component()

    # Parameters derived from footprint and visual inspection.
    # Total length = length + 2 * dx = 40 + 2 * 40 = 120 um.
    # Vertical port separation = dy = 4 um.
    # The gap is a reasonable estimate for a standard coupler.
    coupler_params = {
        "length": 40.0,
        "gap": 0.2,
        "dy": 4.0,
        "dx": 40.0,
        "cross_section": gf.cross_section.cross_section(width=0.5)
    }

    # The gf.components.coupler is the ideal parametric primitive for this shape.
    # It internally constructs two S-bends (using smooth Euler bends by default)
    # and a straight coupling region.
    coupler_device = gf.components.coupler(**coupler_params)

    # Add the created coupler as a reference to the main component.
    coupler_ref = c << coupler_device

    # Expose the ports of the coupler at the top level of our component.
    c.add_ports(coupler_ref.ports)

    # Absorb the reference to flatten the hierarchy and ensure the final
    # GDS has the expected simple geometry.
    c.absorb(coupler_ref)


    return c

# --- FIX START ---
# The original script defined the component function but never called it or
# wrote the result to a file. The following code is necessary to instantiate
# the component and save it as a GDS file.

if __name__ == "__main__":
    # 1. Instantiate the component by calling the function
    my_coupler = directional_coupler_from_image()

    # 2. (Optional but recommended) Show the component in KLayout viewer
    my_coupler.show()

    # 3. Write the component to a GDS file
    my_coupler.write_gds("directional_coupler.gds")
# --- FIX END ---