import gdsfactory as gf

@gf.cell
def directional_coupler_from_image():
    """
    Recreates the directional coupler from the image, which has a distinct
    straight coupling section in the middle, flanked by S-bends.

    Analysis of Target vs. Previous Output:
    - The previous attempt used `gf.components.coupler_symmetric`, which creates a
      continuously curved device without a straight parallel section.
    - The target image clearly shows a central region where the two waveguides
      are straight and parallel for some distance.
    - The `gf.components.coupler` function is the correct primitive for this
      topology, as it includes a `length` parameter to define this straight
      coupling region.
    """
    c = gf.Component()

    # Use gf.components.coupler, which allows for a straight coupling length.
    # The parameters are tuned to match the visual proportions of the target
    # image and adhere to the specified footprint constraint of [120, 4] um.

    # Footprint Calculation:
    # Total Length = length + 2 * dx = 60 + 2 * 30 = 120 um.
    # Total Height = gap + width + 2 * dy = 0.5 + 1.0 + 2 * 1.25 = 4.0 um.
    coupler_device = gf.components.coupler(
        length=60.0,
        gap=0.5,
        dy=1.25,
        dx=30.0,
        cross_section=gf.cross_section.cross_section(width=1.0)
    )

    # Add the coupler instance to our component cell.
    coupler_ref = c << coupler_device

    # Expose the ports and absorb the reference to flatten the geometry.
    c.add_ports(coupler_ref.ports)
    c.absorb(coupler_ref)

    return c

# --- Main execution block ---
# This part instantiates the component and writes it to a GDS file.

if __name__ == "__main__":
    # 1. Instantiate the component by calling the function.
    my_directional_coupler = directional_coupler_from_image()

    # 2. (Optional but recommended) Show the component in a GDS viewer.
    my_directional_coupler.show()

    # 3. Write the component to a GDS file.
    my_directional_coupler.write_gds("directional_coupler.gds")