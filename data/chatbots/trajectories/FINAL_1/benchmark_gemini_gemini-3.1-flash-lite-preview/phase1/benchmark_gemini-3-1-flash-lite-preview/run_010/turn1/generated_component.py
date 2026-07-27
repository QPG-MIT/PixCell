import gdsfactory as gf

@gf.cell
def tapered_triplet_coupler():
    """
    Recreation of the tapered triplet waveguide structure using 
    parametric primitives from the GDSFactory catalog.
    """
    c = gf.Component()
    
    # Define the cross_section object for the waveguide components
    xs = gf.cross_section.cross_section(width=0.3, layer=(1, 0))
    
    # 1. Central Taper (using width1=0.3 to match the waveguide)
    # The center element tapers from 0.3 down to 0.1um.
    center_taper = c << gf.components.taper(length=40, width1=0.3, width2=0.1)
    
    # 2. Top S-bend (curves outward)
    # The S-bend connects offset ports.
    top_arm = c << gf.components.bend_s(size=(40, 0.2), cross_section=xs)
    top_arm.movey(0.5)
    
    # 3. Bottom S-bend (curves outward)
    bot_arm = c << gf.components.bend_s(size=(40, -0.2), cross_section=xs)
    bot_arm.movey(-0.5)
    
    return c

# Generate the component and write the GDS file
if __name__ == "__main__":
    device = tapered_triplet_coupler()
    # Explicitly write the GDS file to the filesystem
    device.write_gds("triplet_coupler.gds")