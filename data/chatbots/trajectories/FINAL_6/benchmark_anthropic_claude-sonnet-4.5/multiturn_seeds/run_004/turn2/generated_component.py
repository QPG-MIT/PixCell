import gdsfactory as gf
import numpy as np

@gf.cell
def cross_device():
    """
    Creates a cross-shaped device with four circular pads at the ends.
    Footprint: 4.7 x 4.7 microns
    """
    c = gf.Component()
    
    # Parameters (in microns)
    total_size = 4.7  # Total footprint
    arm_width = 0.5  # Width of the connecting arms
    pad_diameter = 1.15  # Diameter of the circular pads
    arm_length = 1.5  # Length of exposed arm from center
    
    # Calculate pad center position from origin
    pad_center_offset = total_size/2 - pad_diameter/2
    
    # Create the central cross arms
    h_arm = gf.components.rectangle(
        size=(total_size, arm_width),
        layer=(1, 0),
        centered=True
    )
    
    v_arm = gf.components.rectangle(
        size=(arm_width, total_size),
        layer=(1, 0),
        centered=True
    )
    
    # Start with the cross base
    result = gf.boolean(h_arm, v_arm, operation="or", layer=(1, 0))
    
    # Create circular pads at each end
    # Using circles for the pads
    pad = gf.components.circle(
        radius=pad_diameter/2,
        layer=(1, 0)
    )
    
    # Top pad
    pad_top = pad.copy()
    pad_top.move((0, pad_center_offset))
    result = gf.boolean(result, pad_top, operation="or", layer=(1, 0))
    
    # Bottom pad
    pad_bottom = pad.copy()
    pad_bottom.move((0, -pad_center_offset))
    result = gf.boolean(result, pad_bottom, operation="or", layer=(1, 0))
    
    # Right pad
    pad_right = pad.copy()
    pad_right.move((pad_center_offset, 0))
    result = gf.boolean(result, pad_right, operation="or", layer=(1, 0))
    
    # Left pad
    pad_left = pad.copy()
    pad_left.move((-pad_center_offset, 0))
    result = gf.boolean(result, pad_left, operation="or", layer=(1, 0))
    
    # Add final result to component
    c << result
    
    return c

# Create the device
device = cross_device()

# Save to GDS file
device.write_gds("cross_device.gds")

# Optional: Display the device
print("Device created successfully!")
print(f"Bounding box: {device.bbox}")