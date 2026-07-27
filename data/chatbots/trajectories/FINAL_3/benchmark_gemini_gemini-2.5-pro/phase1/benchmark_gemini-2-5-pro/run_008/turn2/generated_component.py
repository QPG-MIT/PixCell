import gdsfactory as gf
from functools import partial

@gf.cell
def curved_directional_coupler_from_image():
    """
    Recreates the curved directional coupler geometry from the provided image.

    Analysis of the target image and error:
    - The target image shows a continuously curved structure where the waveguides are
      furthest apart at the ends and closest in the middle.
    - The `gf.components.coupler_symmetric` is the correct high-level component for
      this topology.
    - The error `TypeError: bend_euler() got an unexpected keyword argument 'size'`
      indicates that `coupler_symmetric` tries to build its shape using an S-bend
      defined by a `size` tuple, but was given `bend_euler` which doesn't accept `size`.
    - The fix is to provide `gf.components.bend_s` as the bend primitive, which is
      compatible with the `size` argument that `coupler_symmetric` passes internally.
    """
    c = gf.Component()

    # The `coupler_symmetric` component is the correct choice.
    # We fix the error by passing `gf.components.bend_s` as the bend function.
    # The `dx` and `dy` parameters of `coupler_symmetric` will now be correctly
    # passed to `bend_s` to define the shape of each arm.
    # We tune the parameters to visually match the target image.
    coupler_device = gf.components.coupler_symmetric(
        bend=gf.components.bend_s,  # FIX: Use bend_s which accepts a 'size' argument.
        gap=1.0,  # Minimum distance between the two waveguides.
        dy=5.0,   # Vertical separation between input/output and the center line for one S-bend.
        dx=30.0,  # Horizontal length of one S-bend.
        cross_section=gf.cross_section.cross_section(width=1.0) # Using a thicker width for better visual match.
    )

    # Add the coupler instance to our component cell.
    coupler_ref = c << coupler_device

    # Expose the ports and flatten the geometry.
    c.add_ports(coupler_ref.ports)
    c.absorb(coupler_ref)

    return c

# --- Main execution block ---
# This part instantiates the component and writes it to a GDS file.

if __name__ == "__main__":
    # 1. Instantiate the component by calling the function.
    my_curved_coupler = curved_directional_coupler_from_image()

    # 2. (Optional but recommended) Show the component in a GDS viewer.
    my_curved_coupler.show()

    # 3. Write the component to a GDS file.
    my_curved_coupler.write_gds("curved_directional_coupler.gds")