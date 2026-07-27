import gdsfactory as gf

@gf.cell
def patterned_waveguide_device():
    """
    Creates a device composed of 5 central waveguides and 
    symmetrical tapered slab structures.
    """
    c = gf.Component()
    
    # 1. Define the parameters
    device_length = 120
    waveguide_width = 0.2
    
    # Define a cross section for the waveguides
    xs_wg = gf.cross_section.cross_section(width=waveguide_width, layer=(1, 0))
    # Define a cross section for the cladding/slab
    xs_slab = gf.cross_section.cross_section(width=1.0, layer=(2, 0))

    # 2. Add the 5 central waveguides
    # We position them with a pitch of 0.4um centered at y=0
    for i in range(5):
        y_offset = (i - 2) * 0.4
        wg = c << gf.components.straight(length=device_length, cross_section=xs_wg)
        wg.movey(y_offset)

    # 3. Add the top and bottom slab structures
    # We use tapers to create the "flare" effect. 
    # To create a flare that is wide at ends and narrow in the middle, 
    # we use two tapers joined in the center (at x=60).
    
    # Dimensions for the slab flare
    start_width = 0.5
    end_width = 1.2
    
    # Create the top flare using two tapers
    # Left side (narrow to wide)
    top_taper_left = c << gf.components.taper(length=device_length/2, width1=end_width, width2=start_width, cross_section=xs_slab)
    # Right side (wide to narrow)
    top_taper_right = c << gf.components.taper(length=device_length/2, width1=start_width, width2=end_width, cross_section=xs_slab)
    
    # Align the top slabs
    top_taper_left.move((0, 1.2))
    top_taper_right.move((device_length/2, 1.2))
    
    # Create the bottom flare (mirrored)
    bottom_taper_left = c << gf.components.taper(length=device_length/2, width1=end_width, width2=start_width, cross_section=xs_slab)
    bottom_taper_right = c << gf.components.taper(length=device_length/2, width1=start_width, width2=end_width, cross_section=xs_slab)
    
    # Align the bottom slabs
    bottom_taper_left.move((0, -1.2))
    bottom_taper_right.move((device_length/2, -1.2))

    return c

# Create and save the device
if __name__ == "__main__":
    device = patterned_waveguide_device()
    device.write_gds("patterned_device.gds")
    device.show()