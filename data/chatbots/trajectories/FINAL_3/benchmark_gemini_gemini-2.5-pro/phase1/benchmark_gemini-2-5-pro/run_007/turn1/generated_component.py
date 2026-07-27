import gdsfactory as gf

@gf.cell
def directional_coupler_device():
    """
    Creates a parametric directional coupler based on the provided image and
    footprint constraints.

    This function uses the high-level `gf.components.coupler` component,
    which internally combines S-bends and a straight coupling region to
    form the desired geometry.
    """

    # --- 1. Define Parameters from Constraints ---

    # Device footprint from the problem statement
    footprint_width = 120.0  # um
    footprint_height = 4.0   # um

    # Assume standard values for waveguide width and coupling gap
    waveguide_width = 0.5  # um
    coupling_gap = 0.2     # um

    # Decompose the total width into bend and straight sections.
    # A 1/3 split for each of the two bends and the central section is a
    # reasonable interpretation of the device's proportions.
    coupling_length = footprint_width / 3.0
    bend_length_dx = (footprint_width - coupling_length) / 2.0

    # Calculate the required vertical bend height (dy) to achieve the
    # final port-to-port separation given the footprint height.
    # The total height is the sum of the central separation (width + gap)
    # and the vertical travel of the two S-bends (2 * dy).
    center_to_center_separation = waveguide_width + coupling_gap
    bend_height_dy = (footprint_height - center_to_center_separation) / 2.0

    # --- 2. Define the Waveguide Cross-Section ---
    
    # A simple cross-section with the defined width is sufficient.
    xs = gf.cross_section.cross_section(width=waveguide_width)

    # --- 3. Instantiate and Return the Component ---
    
    # The `gf.components.coupler` is the ideal parametric function for this geometry.
    c = gf.components.coupler(
        length=coupling_length,
        gap=coupling_gap,
        dy=bend_height_dy,
        dx=bend_length_dx,
        cross_section=xs,
    )
    return c

# --- Main execution block ---
# This part of the script runs when the file is executed.
if __name__ == "__main__":
    # Create an instance of the component.
    device = directional_coupler_device()
    
    # Write the component to a GDSII file. This was the missing step.
    device.write_gds("directional_coupler.gds")
    
    # Optional: Show the component in the KLayout viewer for verification.
    device.show()