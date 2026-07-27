import gdsfactory as gf

@gf.cell
def custom_mmi_geometry():
    """Recreates the geometry of the provided device."""
    c = gf.Component("mmi_like_device")

    # Define standard cross-section for the thin straight waveguides
    xs_thin = gf.cross_section.cross_section(width=1.0, layer=(1, 0))

    # 1. Main rectangular body
    # The footprint constraints [25, 10] match the main central body's dimensions
    body_width = 25.0
    body_height = 10.0
    c << gf.components.rectangle(
        size=(body_width, body_height), 
        layer=(1, 0), 
        centered=True
    )

    # 2. Top Output Arms (Taper + Straight sections)
    @gf.cell
    def top_arm():
        arm_c = gf.Component("top_arm")
        
        # Taper transitioning from thick (body connection) to thin (straight waveguide)
        t = arm_c << gf.components.taper(
            length=5.0, 
            width1=3.0, 
            width2=1.0
        )
        
        # Straight waveguide extension
        s = arm_c << gf.components.straight(
            length=4.0, 
            cross_section=xs_thin
        )
        s.connect("o1", t.ports["o2"])
        
        return arm_c

    arm_comp = top_arm()
    
    # 4 evenly spaced arms. Base width=3, spacing=3 -> Pitch=6
    # Centers at -9, -3, 3, 9 to perfectly fit within the 25um width symmetrically
    x_positions = [-9.0, -3.0, 3.0, 9.0]

    for x in x_positions:
        arm_ref = c << arm_comp
        # Default taper faces East (0 deg). Rotate 90 deg so it points North (+y).
        arm_ref.rotate(90)
        # Move the thick base (which remains at the rotation origin 0,0) to the top edge
        arm_ref.move((x, body_height / 2))

    # 3. Bottom Input Taper
    taper_bot = c << gf.components.taper(
        length=4.0, 
        width1=3.0, 
        width2=1.0
    )
    # Rotate -90 deg so it points South (-y).
    taper_bot.rotate(-90)
    # Move the thick base (which remains at 0,0) to the center of the bottom edge
    taper_bot.move((0, -body_height / 2))

    return c

if __name__ == "__main__":
    # Create the component
    device = custom_mmi_geometry()
    
    # Save to GDS file (this resolves the "No GDS file produced" error)
    device.write_gds("custom_mmi_geometry.gds")