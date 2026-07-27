import gdsfactory as gf

def serpentine_waveguide_device():
    c = gf.Component()
    
    # Define cross-section for waveguides
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # Parameters based on the footprint and visual analysis
    total_width = 120.0
    total_height = 4.0
    waveguide_width = 0.5
    gap_between_waveguides = 0.5
    num_waveguides = 5  # Based on visual count in the central section
    
    # Create multiple parallel waveguides with serpentine pattern
    for i in range(num_waveguides):
        # Calculate y position for this waveguide
        y_pos = (i - (num_waveguides - 1) / 2) * (waveguide_width + gap_between_waveguides)
        
        # Create a more complex serpentine path
        path = gf.Path()
        
        # Start at left side
        path.append(gf.path.straight(length=10))
        
        # Go up to create the top curve
        path.append(gf.path.straight(length=10))
        
        # Curve to the right
        path.append(gf.path.euler(radius=10, angle=90))
        
        # Go right across the top
        path.append(gf.path.straight(length=100))
        
        # Curve down
        path.append(gf.path.euler(radius=10, angle=90))
        
        # Go down
        path.append(gf.path.straight(length=20))
        
        # Curve to the left
        path.append(gf.path.euler(radius=10, angle=90))
        
        # Go left across the bottom
        path.append(gf.path.straight(length=100))
        
        # Curve up
        path.append(gf.path.euler(radius=10, angle=90))
        
        # Go up
        path.append(gf.path.straight(length=10))
        
        # Go left to complete
        path.append(gf.path.straight(length=10))
        
        # Extrude the path
        waveguide = gf.path.extrude(path, cross_section=xs)
        waveguide_ref = c << waveguide
        
        # Move to correct position
        waveguide_ref.move((0, y_pos))
        
        # Add ports
        c.add_port(f"o1_{i+1}", port=waveguide_ref.ports["o1"])
        c.add_port(f"o2_{i+1}", port=waveguide_ref.ports["o2"])
    
    return c

# Create and save the device
device = serpentine_waveguide_device()
device.write_gds("serpentine_waveguide.gds")