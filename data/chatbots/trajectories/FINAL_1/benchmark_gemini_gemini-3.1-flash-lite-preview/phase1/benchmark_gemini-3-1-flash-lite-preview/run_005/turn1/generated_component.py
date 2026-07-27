import gdsfactory as gf

@gf.cell
def adiabatic_taper_device(
    length: float = 40.0,
    width_wide: float = 0.6,
    width_narrow: float = 0.1,
    y_offset: float = 0.6,
):
    """
    Creates an adiabatic taper structure based on the provided footprint.
    
    The structure consists of:
    - Central taper: Width decreasing from wide to narrow.
    - Outer tapers: Width increasing from narrow to wide.
    """
    c = gf.Component()

    # Define the taper primitive
    # The center taper: wide to narrow
    taper_center = gf.components.taper(
        length=length, 
        width1=width_wide, 
        width2=width_narrow
    )

    # The outer tapers: narrow to wide
    taper_outer = gf.components.taper(
        length=length, 
        width1=width_narrow, 
        width2=width_wide
    )

    # Add references to the main component
    # Center piece
    center_ref = c << taper_center
    center_ref.center = (length / 2, 0)

    # Top piece (offset positive y)
    top_ref = c << taper_outer
    top_ref.center = (length / 2, y_offset)

    # Bottom piece (offset negative y)
    bot_ref = c << taper_outer
    bot_ref.center = (length / 2, -y_offset)

    return c

# Create the device with the requested 40um length
device = adiabatic_taper_device(length=40.0)

# Save the resulting GDSII file
device.write_gds("adiabatic_taper.gds")

# View the component (optional)
# device.show()