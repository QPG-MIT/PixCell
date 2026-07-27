import gdsfactory as gf
import pathlib

# Define the waveguide cross-section.
# A standard single-mode silicon waveguide width is 0.5 um.
xs = gf.cross_section.cross_section(width=0.5)

# Derive parameters from the provided footprint [120, 4] and visual analysis.
# Total width = 120 um. We allocate 30 um for each bend (dx) and 60 um for the coupling length.
# 2 * 30 + 60 = 120 um.
coupling_length = 60.0
bend_horizontal_length = 30.0

# Total height = 4 um. This is the port-to-port separation (dy) + waveguide width.
# dy = 4.0 - 0.5 = 3.5 um.
port_vertical_separation = 3.5

# The gap is the narrow separation in the coupling region. A value of 0.2 um is a
# reasonable estimate based on the drawing.
coupling_gap = 0.2

# Create the directional coupler using the high-level parametric primitive.
# This function constructs the shape from S-bends and straight waveguides.
c = gf.components.coupler(
    length=coupling_length,
    gap=coupling_gap,
    dy=port_vertical_separation,
    dx=bend_horizontal_length,
    cross_section=xs,
)

# --- FIX ---
# The following lines were missing or commented out.
# They are now active to ensure the GDS file is written.

# Get the directory of the current script
output_dir = pathlib.Path(__file__).parent.absolute()
# Define the output filepath
output_path = output_dir / "directional_coupler.gds"

# Write the component to a GDS file
c.write_gds(output_path)

print(f"GDS file saved to: {output_path}")

# Optional: To display the component in a viewer like KLayout
# c.show()