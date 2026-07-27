import gdsfactory as gf

@gf.cell
def recreate_original_device():
    """
    Recreates the device geometry using continuous path extrusion 
    to ensure smooth flaring and avoid intersection artifacts.
    """
    c = gf.Component("device_v3")
    layer = (1, 0)
    total_width = 120.0 # um
    
    # 1. CENTRAL SECTION
    # 5 parallel thin lines running the full width.
    xs_center = gf.cross_section.cross_section(
        sections=[
            gf.Section(width=0.08, offset=y, layer=layer) 
            for y in [-0.32, -0.16, 0, 0.16, 0.32]
        ]
    )
    center_wg = c << gf.components.straight(length=total_width, cross_section=xs_center)
    center_wg.x = 0
    center_wg.y = 0

    # 2. DEFINE THE "COMB" CROSS-SECTION
    # Consists of 1 thick base and 5 thinner lines above it.
    # Defined relative to the base center (offset 0) for easy pathing.
    xs_comb = gf.cross_section.cross_section(
        sections=[
            gf.Section(width=0.5, offset=0, layer=layer),     # Thick base
            gf.Section(width=0.08, offset=0.35, layer=layer), # Line 1
            gf.Section(width=0.08, offset=0.50, layer=layer), # Line 2
            gf.Section(width=0.08, offset=0.65, layer=layer), # Line 3
            gf.Section(width=0.08, offset=0.80, layer=layer), # Line 4
            gf.Section(width=0.08, offset=0.95, layer=layer), # Line 5
        ]
    )

    # 3. CREATE THE FLARING PATH
    # We construct a single path: (flare up) + (straight) + (flare up)
    # Total width must be 120um. We'll use 15um for each flare and 90um for the middle.
    flare_angle = 25  # Increased angle for a more distinct 'flare'
    flare_radius = 30 # Tighter radius to match the original image sharp look
    
    # Build path from components
    p_right = gf.path.euler(radius=flare_radius, angle=flare_angle)
    p_mid = gf.path.straight(length=90)
    p_left = p_right.copy().mirror((0, 1)) # Mirror to face the other way
    
    # Assemble the full path
    full_path = p_left + p_mid + p_right
    
    # 4. FINAL ASSEMBLY
    # Extrude the top block
    top_geo = gf.path.extrude(full_path, cross_section=xs_comb)
    top_ref = c << top_geo
    top_ref.x = 0
    top_ref.y = 1.0 # Offset from center
    
    # Create the bottom block by mirroring the top reference.
    # This ensures perfect symmetry and maintains the cross-section orientation.
    bottom_ref = c << top_geo
    bottom_ref.mirror((1, 0)) # Mirror across X-axis
    bottom_ref.x = 0
    bottom_ref.y = -1.0 # Offset below center

    return c

if __name__ == "__main__":
    device = recreate_original_device()
    
    # Explicitly write the GDS file
    filename = "corrected_device_geometry.gds"
    device.write_gds(filename)
    
    print(f"Success: Geometry rendered to {filename}")
    # device.show()