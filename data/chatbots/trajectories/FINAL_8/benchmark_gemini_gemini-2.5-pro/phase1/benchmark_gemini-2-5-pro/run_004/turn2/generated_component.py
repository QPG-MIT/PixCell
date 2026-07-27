import gdsfactory as gf
from gdsfactory.cross_section import Section

@gf.cell
def create_asymmetric_device():
    """
    Creates an asymmetric device with a lower U-bend and an upper straight bus.
    Each part has a distinct multi-line cross-section.
    """
    c = gf.Component("AsymmetricDevice")

    # --- 1. Define Parameters (Inferred from image) ---
    
    # Lower U-bend parameters
    lower_bend_radius = 20.0
    lower_straight_length = 60.0
    
    # Upper straight bus parameters
    upper_length = 2 * lower_bend_radius + lower_straight_length

    # Vertical separation between the two structures
    vertical_separation = 40.0
    
    layer = (1, 0)

    # --- 2. Define Cross-Sections for Each Part ---

    # Cross-section for the lower U-bend (two wide lines)
    xs_lower = gf.cross_section.cross_section(
        sections=(
            Section(width=3.0, offset=-2.5, layer=layer),
            Section(width=3.0, offset=2.5, layer=layer),
        )
    )

    # Cross-section for the upper straight bus (three narrow lines)
    xs_upper = gf.cross_section.cross_section(
        sections=(
            Section(width=1.0, offset=-2.0, layer=layer),
            Section(width=1.0, offset=0, layer=layer),
            Section(width=1.0, offset=2.0, layer=layer),
        )
    )

    # --- 3. Create the Lower U-bend using a Path ---
    
    # A path is a robust way to define a continuous route
    p = gf.Path()
    p.append(gf.path.euler(radius=lower_bend_radius, angle=-90))
    p.append(gf.path.straight(length=lower_straight_length))
    p.append(gf.path.euler(radius=lower_bend_radius, angle=90))

    # Extrude the path with the lower cross-section to create the component
    lower_ubend = gf.path.extrude(p, cross_section=xs_lower)
    
    # --- 4. Create the Upper Straight Bus ---
    
    upper_bus = gf.components.straight(length=upper_length, cross_section=xs_upper)
    
    # --- 5. Assemble and Position the Components ---
    
    # Add references to the main component
    ubend_ref = c << lower_ubend
    bus_ref = c << upper_bus
    
    # Position the components relative to each other
    # Place the U-bend at the bottom, starting at (0, 0)
    ubend_ref.xmin = 0
    ubend_ref.ymin = 0
    
    # Place the straight bus above the U-bend with a defined separation
    bus_ref.xmin = 0
    bus_ref.ymin = ubend_ref.ymax + vertical_separation
    
    return c


# --- Main execution block to generate the GDS file ---
if __name__ == "__main__":
    # Create an instance of the device
    device_to_write = create_asymmetric_device()

    # Write the GDS file to disk
    device_to_write.write_gds("output.gds")
    
    print("GDS file 'output.gds' for the new device has been successfully generated.")
    
    # Optional: uncomment the line below to show the geometry in a viewer
    # device_to_write.show()