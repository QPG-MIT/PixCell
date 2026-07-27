import gdsfactory as gf
import pathlib

@gf.cell
def create_waveguide_cross_flare():
    """
    Creates a device with a waveguide crossing on the input and a flare
    on the output, connected by a parallel straight section.
    """

    # --- 1. Define Parameters (estimated from image proportions) ---
    waveguide_width = 0.5
    gap = 0.5  # Central gap between the parallel waveguides
    coupling_length = 30.0

    # Parameters for the end sections
    io_length = 15.0  # The horizontal length of the cross and flare sections
    io_separation = 5.0  # The final port-to-port vertical distance on both ends

    # --- 2. Create the main component and define a common cross-section ---
    c = gf.Component("waveguide_cross_flare")
    xs = gf.cross_section.cross_section(width=waveguide_width)

    # --- 3. Create and Assemble the Subcomponents ---

    # A. Create the central parallel waveguide section
    coupler_section = gf.components.coupler_straight(
        length=coupling_length, gap=gap, cross_section=xs
    )
    coupler_ref = c << coupler_section

    # B. Create the right-side FLARE section
    # Calculate the vertical distance one bend needs to travel
    dy_flare = (io_separation / 2) - ((gap + waveguide_width) / 2)
    bend_flare = gf.components.bend_s(size=(io_length, dy_flare), cross_section=xs)
    
    flare_top = c << bend_flare
    flare_bot = c << bend_flare
    flare_bot.mirror_y()  # Mirror the bottom bend across the x-axis for symmetry
    
    flare_top.connect("o1", coupler_ref.ports["o3"])
    flare_bot.connect("o1", coupler_ref.ports["o4"])

    # C. Create the left-side CROSSING section
    # Calculate the vertical distance for one bend to travel across the center axis
    y_start = io_separation / 2.0
    y_end = -(gap + waveguide_width) / 2.0
    dy_cross = y_end - y_start

    bend_cross = gf.components.bend_s(size=(io_length, dy_cross), cross_section=xs)

    cross_top_to_bot = c << bend_cross
    cross_bot_to_top = c << bend_cross
    
    # Transform the references for the left side
    cross_top_to_bot.mirror()  # Mirror across y-axis to point left
    cross_bot_to_top.mirror()  # Mirror across y-axis
    cross_bot_to_top.mirror_y()# Then mirror across x-axis

    # CRITICAL: Connect them in a crossing configuration
    # Top input waveguide goes to the BOTTOM straight waveguide
    cross_top_to_bot.connect("o2", coupler_ref.ports["o2"])
    
    # Bottom input waveguide goes to the TOP straight waveguide
    cross_bot_to_top.connect("o2", coupler_ref.ports["o1"])

    # --- 4. Add External Ports to the final device ---
    c.add_port("o1", port=cross_top_to_bot.ports["o1"])
    c.add_port("o2", port=cross_bot_to_top.ports["o1"])
    c.add_port("o3", port=flare_top.ports["o2"])
    c.add_port("o4", port=flare_bot.ports["o2"])

    return c

# --- Main execution block to generate and save the GDS file ---
if __name__ == "__main__":
    # Instantiate the component
    device = create_waveguide_cross_flare()
    
    # Optional: Display the component in the KLayout viewer for verification
    # device.show()
    
    # Save the component to a GDS file
    output_filename = "waveguide_cross_flare.gds"
    device.write_gds(output_filename)
    
    # Add a print statement to confirm completion
    print(f"Successfully generated GDS file: {pathlib.Path(output_filename).resolve()}")