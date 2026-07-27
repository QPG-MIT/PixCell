import gdsfactory as gf

@gf.cell
def sine_taper_waveguide():
    """
    Creates a single waveguide with a width that varies sinusoidally.
    The waveguide is narrowest at the ends and widest in the center,
    matching the provided image.
    """
    # 1. Define the geometric parameters for the device.
    # These values are chosen to match the visual proportions of the image.
    length = 18.0
    width_end = 0.5
    width_center = 1.0

    # 2. Define the cross-sections for the narrow (end) and wide (center) parts.
    xs_end = gf.cross_section.cross_section(width=width_end)
    xs_center = gf.cross_section.cross_section(width=width_center)

    # 3. Create the transition objects for each half of the device.
    # A 'sine' width_type creates a smooth, half-period sinusoidal taper.
    # First half: Tapers from narrow (end) to wide (center).
    transition_in = gf.path.transition(
        cross_section1=xs_end, cross_section2=xs_center, width_type="sine"
    )
    # Second half: Tapers from wide (center) back to narrow (end).
    transition_out = gf.path.transition(
        cross_section1=xs_center, cross_section2=xs_end, width_type="sine"
    )

    # 4. Create the straight path segments for each half.
    path_half = gf.path.straight(length=length / 2)

    # 5. Extrude the path segments using the corresponding transitions.
    wg_half1 = gf.path.extrude_transition(path_half, transition=transition_in)
    wg_half2 = gf.path.extrude_transition(path_half, transition=transition_out)

    # 6. Assemble the two halves into the final component.
    c = gf.Component("sine_taper_waveguide")
    
    # Add the first half as a reference.
    ref1 = c << wg_half1
    
    # Add the second half as a reference.
    ref2 = c << wg_half2
    
    # Connect the start of the second half to the end of the first half.
    ref2.connect("o1", ref1.ports["o2"])

    # Center the final component at the origin.
    c.movex(-length / 2)

    return c

# Main script execution block to generate the GDS file.
if __name__ == "__main__":
    # Instantiate the component.
    recreated_device = sine_taper_waveguide()

    # Write the component to a GDSII file.
    recreated_device.write_gds("sine_taper_waveguide.gds")

    # The following line can be uncommented to display the layout visually.
    # recreated_device.show()
    # print("GDS file 'sine_taper_waveguide.gds' has been generated.")