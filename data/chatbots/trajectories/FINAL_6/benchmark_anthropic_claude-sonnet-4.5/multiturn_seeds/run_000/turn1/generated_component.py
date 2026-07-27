import gdsfactory as gf
import numpy as np

@gf.cell
def petal_cross_device():
    """
    Creates a four-petal cross structure with rounded elliptical arms.
    
    The device has 4-fold rotational symmetry with elliptical petals
    extending from the center in cardinal directions.
    """
    c = gf.Component()
    
    # Dimensions based on 4.7 x 4.7 um footprint
    # Each arm extends ~2.35 um from center to edge
    arm_radial_length = 2.0  # Length of each elliptical petal (radial direction)
    arm_tangential_width = 1.1  # Width of each petal (tangential direction)
    arm_center_offset = 1.15  # Distance of ellipse center from origin
    
    # Create one petal as an ellipse
    # For a vertical petal: x_radius is tangential, y_radius is radial
    petal_template = gf.components.ellipse(
        radii=(arm_tangential_width/2, arm_radial_length/2),
        layer=(1, 0)
    )
    
    # Add 4 petals at 0°, 90°, 180°, 270°
    for angle in [0, 90, 180, 270]:
        petal = c << petal_template
        petal.rotate(angle)
        
        # Position each petal radiating from center
        rad_angle = np.radians(angle)
        x_offset = arm_center_offset * np.cos(rad_angle)
        y_offset = arm_center_offset * np.sin(rad_angle)
        petal.move((x_offset, y_offset))
    
    return c

# Create and save the device
device = petal_cross_device()
device.write_gds("petal_cross_device.gds")

# Optional: show the device
print(f"Device created with bounding box: {device.bbox}")
device.show()