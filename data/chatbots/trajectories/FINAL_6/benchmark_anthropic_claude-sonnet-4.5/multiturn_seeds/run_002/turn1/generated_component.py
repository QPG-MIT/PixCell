import gdsfactory as gf
import numpy as np

@gf.cell
def cross_resonator(
    petal_length: float = 2.2,
    petal_width: float = 0.9,
    center_size: float = 1.0,
    layer: tuple = (1, 0)
) -> gf.Component:
    """
    Create a four-petal cross-shaped resonator.
    
    Args:
        petal_length: Length of each petal from center
        petal_width: Width of each petal
        center_size: Size of central overlap region
        layer: GDS layer tuple
    
    Returns:
        Component with cross-shaped geometry
    """
    c = gf.Component()
    
    # Create the four petals as ellipses positioned in a cross pattern
    # Each petal is an ellipse with major axis along its extension direction
    
    # Calculate ellipse radii
    # Major radius (along petal length)
    major_radius = petal_length
    # Minor radius (petal width)
    minor_radius = petal_width / 2
    
    # Create four ellipses at 0, 90, 180, 270 degrees
    angles = [0, 90, 180, 270]
    
    for angle in angles:
        # Create ellipse
        ellipse = gf.components.ellipse(
            radii=(major_radius, minor_radius),
            layer=layer
        )
        
        # Add as reference and rotate
        ref = c << ellipse
        ref.rotate(angle)
    
    return c

# Create the device
device = cross_resonator(
    petal_length=2.2,
    petal_width=0.9,
    center_size=1.0
)

# Save to GDS
device.write_gds("cross_resonator.gds")

# Optional: display the device
device.show()

print(f"Device created with footprint: {device.dxsize:.2f} x {device.dysize:.2f} um")