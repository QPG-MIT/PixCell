import gdsfactory as gf

@gf.cell
def flared_device():
    """
    Creates a flared waveguide structure consisting of 5 parallel strands.
    Each strand is composed of an S-bend transition, using Euler bends for
    adiabatic curvature.
    """
    c = gf.Component()
    
    # Define the Cross Section
    xs = gf.cross_section.cross_section(width=0.3, layer=(1, 0))
    
    # Parameters
    num_strands = 5
    spacing = 1.0  # Spacing between waveguides
    
    # We will iterate to create 5 strands, spacing them apart
    for i in range(num_strands):
        # Calculate Y position offset
        y_offset = (i - (num_strands - 1) / 2) * spacing
        
        # Build a single strand using path primitives
        # A strand is essentially a smooth path transition (S-bend)
        # Using the Path functions as per the catalog
        path = gf.Path()
        path.append(gf.path.straight(length=10)) # Top straight
        path.append(gf.path.euler(radius=15, angle=90, p=1)) # Flare out
        path.append(gf.path.straight(length=20)) # Middle straight
        path.append(gf.path.euler(radius=15, angle=-90, p=1)) # Flare in
        path.append(gf.path.straight(length=10)) # Bottom straight
        
        # Extrude the path into a waveguide component
        strand = gf.path.extrude(path, cross_section=xs)
        
        # Add to main component and move to correct offset
        ref = c << strand
        ref.movey(y_offset)
        
    return c

if __name__ == "__main__":
    # Create the device
    device = flared_device()
    
    # Output the device size using the correct properties
    print(f"Device size: {device.xsize:.2f} um x {device.ysize:.2f} um")
    
    # Save the file
    device.write_gds("flared_device.gds")
    
    # Optional: view the device
    # device.show()