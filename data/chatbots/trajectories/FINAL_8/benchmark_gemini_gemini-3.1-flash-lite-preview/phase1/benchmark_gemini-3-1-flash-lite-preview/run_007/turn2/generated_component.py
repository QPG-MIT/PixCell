import gdsfactory as gf

@gf.cell(check_instances=False)
def patterned_waveguide_device():
    """
    Creates a device composed of 5 central horizontal waveguides
    with symmetric flared slab structures.
    """
    c = gf.Component()
    
    # Parameters
    device_length = 120
    wg_spacing = 1.0
    
    # 1. Define standard cross sections
    xs_wg = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    xs_slab = gf.cross_section.cross_section(width=1.0, layer=(1, 0))

    # 2. Add the 5 central waveguides
    # Centering them around y=0
    for i in range(5):
        y_offset = (i - 2) * wg_spacing
        wg = c << gf.components.straight(length=device_length, cross_section=xs_wg)
        wg.movey(y_offset)

    # 3. Create the flared 'wing' structures (Top and Bottom)
    # The image shows a structure that flares out at the ends.
    # We use tapers to create this flare.
    
    flare_length = device_length
    
    # Top flare
    top_flare = c << gf.components.taper(length=flare_length, width1=10, width2=2, cross_section=xs_slab)
    top_flare.movey(6) # Position above the waveguides
    
    # Bottom flare
    bot_flare = c << gf.components.taper(length=flare_length, width1=10, width2=2, cross_section=xs_slab)
    bot_flare.movey(-6) # Position below the waveguides
    
    # 4. Create the central solid block seen in the image
    center_block = c << gf.components.rectangle(size=(device_length, 4), layer=(1, 0), centered=True)
    center_block.movey(0)

    return c

if __name__ == "__main__":
    device = patterned_waveguide_device()
    device.write_gds("patterned_device_fixed.gds")
    device.show()