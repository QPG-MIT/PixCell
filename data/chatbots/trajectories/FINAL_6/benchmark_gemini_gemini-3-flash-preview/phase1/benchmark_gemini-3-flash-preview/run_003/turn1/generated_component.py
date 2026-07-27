import gdsfactory as gf

@gf.cell
def recreate_cross_device():
    """
    Recreates the cross-shaped device with almond-like arms and rectangular tips.
    Footprint: 4.7um x 4.7um
    """
    c = gf.Component("cross_device")
    
    # 1. Define dimensions based on the 4.7um footprint
    # Total distance from center to tip is 4.7 / 2 = 2.35 um
    total_radius = 2.35
    tip_length = 0.45
    tip_width = 0.3
    bulb_length = total_radius - tip_length  # 1.9 um
    bulb_width = 1.0  # Estimated max width of the petal
    
    # 2. Create the primitives for one arm
    # The bulbous part is modeled with an ellipse
    bulb = gf.components.ellipse(radii=(bulb_length / 2, bulb_width / 2), layer=(1, 0))
    # The tip is a simple rectangle
    tip = gf.components.rectangle(size=(tip_length, tip_width), layer=(1, 0))
    
    # 3. Assemble a single arm component
    arm = gf.Component("single_arm")
    
    # Position the bulb so its 'base' (left side) is at the origin (0,0)
    # The center of the ellipse is moved by half its length
    bulb_ref = arm << bulb
    bulb_ref.movex(bulb_length / 2)
    
    # Position the tip at the end of the bulb
    # The center of the rectangle is moved to (bulb_length + tip_length/2)
    tip_ref = arm << tip
    tip_ref.movex(bulb_length + tip_length / 2)
    
    # 4. Create the full structure by placing 4 rotated instances of the arm
    # This ensures perfect 90-degree symmetry as seen in the image
    for angle in [0, 90, 180, 270]:
        arm_ref = c << arm
        arm_ref.rotate(angle)
    
    # 5. Optional: Use a boolean operation to merge the shapes into a single polygon
    # This satisfies the requirement of using boolean operations for composition
    device_union = gf.boolean(A=c, B=c, operation="or", layer=(1, 0))
    
    return device_union

if __name__ == "__main__":
    # Create the component
    my_device = recreate_cross_device()
    
    # Write to GDS for verification
    my_device.write_gds("cross_device.gds")
    
    # Show the component (if in a GUI environment)
    my_device.show()