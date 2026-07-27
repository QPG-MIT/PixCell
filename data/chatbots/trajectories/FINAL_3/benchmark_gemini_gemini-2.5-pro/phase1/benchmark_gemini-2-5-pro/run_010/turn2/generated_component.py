import gdsfactory as gf
import pathlib

# --- FIX ---
# Instead of relying on a registered name, we create the cross-section object
# and store it in a variable `xs`. This object is then passed directly to the
# component function, which is the most robust method.
xs = gf.cross_section.strip(width=0.5)

# Parameters derived from footprint [120, 4] and visual inspection
footprint_x = 120.0
footprint_y = 4.0
wg_width = 0.5 # This must match the width in the cross-section definition

# Allocate approximately half the total length to the straight coupling region
coupling_length = 60.0
coupling_gap = 0.2  # A reasonable estimate for the coupling gap

# Calculate the horizontal length (dx) of the bend regions
bend_horizontal_length = (footprint_x - coupling_length) / 2.0

# Calculate the vertical port separation (dy) from the footprint.
# The footprint's y-dimension is the distance between the outer edges.
# The 'dy' parameter for the coupler is the center-to-center distance.
port_vertical_separation = footprint_y - wg_width

# The target image requires a standard S-bend (based on Euler curves).
# We explicitly specify the bend component to use.
s_bend_function = gf.components.bend_s

# Create the directional coupler using the high-level parametric primitive.
c = gf.components.coupler(
    length=coupling_length,
    gap=coupling_gap,
    dy=port_vertical_separation,
    dx=bend_horizontal_length,
    cross_section=xs,           # Pass the cross-section object directly
    bend=s_bend_function        # Explicitly specify the correct bend type
)

# --- GDS File Output ---
# Get the directory of the current script to save the GDS file alongside it.
output_dir = pathlib.Path(__file__).parent.absolute()
output_path = output_dir / "directional_coupler_final.gds"

# Write the component to a GDSII file.
c.write_gds(output_path)

print(f"GDS file successfully saved to: {output_path}")

# Optional: To display the component in a viewer like KLayout for verification.
# c.show(show_ports=True)