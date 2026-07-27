import gdsfactory as gf
import numpy as np

@gf.cell
def cross_resonator(
    horizontal_width: float = 4.6,
    horizontal_height: float = 0.7,
    vertical_width: float = 0.7,
    vertical_height: float = 4.6,
    layer: tuple = (1, 0)
) -> gf.Component:
    """
    Create a four-petal cross-shaped resonator with asymmetric petals.
    
    Args:
        horizontal_width: Width of horizontal ellipse (left-right extent)
        horizontal_height: Height of horizontal ellipse
        vertical_width: Width of vertical ellipse
        vertical_height: Height of vertical ellipse (up-down extent)
        layer: GDS layer tuple
    
    Returns:
        Component with cross-shaped geometry
    """
    c = gf.Component()
    
    # Create horizontal ellipse (wide and flat)
    horizontal_ellipse = gf.components.ellipse(
        radii=(horizontal_width / 2, horizontal_height / 2),
        layer=layer
    )
    h_ref = c << horizontal_ellipse
    
    # Create vertical ellipse (tall and narrow)
    vertical_ellipse = gf.components.ellipse(
        radii=(vertical_width / 2, vertical_height / 2),
        layer=layer
    )
    v_ref = c << vertical_ellipse
    
    return c

# Create the device with dimensions to match the target
device = cross_resonator(
    horizontal_width=4.6,
    horizontal_height=0.7,
    vertical_width=0.7,
    vertical_height=4.6
)

# Save to GDS
device.write_gds("cross_resonator.gds")

# Optional: display the device
device.show()

print(f"Device created with footprint: {device.dxsize:.2f} x {device.dysize:.2f} um")