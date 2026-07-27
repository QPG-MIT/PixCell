import gdsfactory as gf
import numpy as np

@gf.cell
def directional_coupler_from_image():
    """
    Recreates the device from the image, which consists of two parallel
    waveguides with smoothly varying widths.

    Analysis of Error and Correction:
    - The previous code failed with a `TypeError` because the function
      `gf.path.extrude_transition` was called with an incorrect keyword argument `path`.
    - The function signature expects the path object as the first positional
      argument. The fix is to call it as `gf.path.extrude_transition(path_object, transition=...)`.

    Corrected Implementation Strategy:
    The overall strategy remains the same as it correctly addresses the geometric
    requirements of the target image. The only change is the correction of the
    function call syntax.
    1. Define cross-sections for the wide ends and the narrow center.
    2. Create a `gf.path.transition` to define the taper shape.
    3. Build one half of the waveguide (wide-to-narrow) by extruding a path of
       `length/2` with this transition.
    4. Create the full tapered waveguide by connecting this half to a mirrored copy.
    5. Place two instances of this complete tapered waveguide in parallel.
    """
    c = gf.Component()

    # --- Step 1: Define Parameters from Footprint [120, 4] and Image ---
    length = 120.0
    total_height = 4.0

    # Estimate geometric parameters from visual inspection of the target.
    gap = 1.0
    width_wide = (total_height - gap) / 2.0  # (4.0 - 1.0) / 2.0 = 1.5
    # Make the center slightly narrower for a more pronounced taper.
    width_narrow = 0.4

    # --- Step 2: Create a single, complete tapered waveguide component ---
    @gf.cell
    def tapered_waveguide(
        length: float, width_wide: float, width_narrow: float
    ):
        """Creates a single waveguide that tapers from wide to narrow and back."""
        wg = gf.Component()

        # Define the cross-sections for the wide and narrow parts
        xs_wide = gf.cross_section.cross_section(width=width_wide)
        xs_narrow = gf.cross_section.cross_section(width=width_narrow)

        # Create the transition from wide to narrow
        taper_transition = gf.path.transition(
            cross_section1=xs_wide, cross_section2=xs_narrow, width_type="sine"
        )

        # Create the path for one half of the taper (wide to narrow)
        path_half = gf.path.straight(length=length / 2)

        # Extrude the path to create the taper-down section.
        # FIX: Pass the path object as a positional argument.
        taper_down = gf.path.extrude_transition(path_half, transition=taper_transition)

        # Create the taper-up section by mirroring the taper-down section
        taper_up = taper_down.mirror()

        # Add both sections to the component
        ref_down = wg << taper_down
        ref_up = wg << taper_up

        # Connect the narrow ends together
        ref_up.connect("o1", ref_down.ports["o2"])

        # Add the external ports
        wg.add_port("o1", port=ref_down.ports["o1"])
        wg.add_port("o2", port=ref_up.ports["o2"])
        return wg

    # Instantiate the tapered waveguide sub-component
    tapered_wg_unit = tapered_waveguide(
        length=length, width_wide=width_wide, width_narrow=width_narrow
    )

    # --- Step 3: Assemble the final device with two parallel waveguides ---
    wg_top = c << tapered_wg_unit
    wg_bottom = c << tapered_wg_unit

    # Position the two waveguides symmetrically around the y=0 axis
    y_position = (gap + width_wide) / 2.0
    wg_top.y = y_position
    wg_bottom.y = -y_position

    # --- Step 4: Expose the ports for external connections ---
    c.add_port("o1", port=wg_bottom.ports["o1"])
    c.add_port("o2", port=wg_top.ports["o1"])
    c.add_port("o3", port=wg_top.ports["o2"])
    c.add_port("o4", port=wg_bottom.ports["o2"])

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