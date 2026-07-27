import gdsfactory as gf

@gf.cell
def create_directional_coupler():
  """
  Generates a symmetric directional coupler component based on the provided
  image and footprint constraints using GDSFactory.

  The component's dimensions are derived from the footprint [120, 4] um.
  """
  # Define a standard waveguide cross-section. A width of 0.5 um is assumed.
  xs = gf.cross_section.cross_section(width=0.5)

  # --- Derive parameters from the footprint [120, 4] ---

  # The total component height is the center-to-center port separation (dy)
  # plus the waveguide width.
  # 4.0 = dy + width -> dy = 4.0 - 0.5 = 3.5 um.
  port_separation_dy = 3.5

  # The total component length is the straight coupling length plus the
  # horizontal length of the two S-bends (2 * dx).
  # We split the 120 um total length to match the image proportions.
  # length = 60 um, 2 * dx = 60 um -> dx = 30 um.
  coupling_length = 60.0
  s_bend_length_dx = 30.0

  # A standard gap for the coupling region is assumed.
  coupling_gap = 0.2

  # Create the directional coupler using the high-level parametric component.
  # This function is the most appropriate way to generate this standard geometry.
  coupler_device = gf.components.coupler(
      length=coupling_length,
      gap=coupling_gap,
      dy=port_separation_dy,
      dx=s_bend_length_dx,
      cross_section=xs,
  )

  return coupler_device

# This block ensures the code runs only when the script is executed directly.
if __name__ == "__main__":
    # Create an instance of the component.
    device = create_directional_coupler()

    # FIX: A GDS file is not produced unless explicitly written to disk.
    # The following line saves the created component to a file named 'output.gds'.
    device.write_gds("output.gds")

    # You can uncomment the following lines to inspect the component if running locally
    # device.show(show_ports=True)
    # print(f"Component '{device.name}' successfully written to 'output.gds'")
    # print(f"Device size: {device.size}")