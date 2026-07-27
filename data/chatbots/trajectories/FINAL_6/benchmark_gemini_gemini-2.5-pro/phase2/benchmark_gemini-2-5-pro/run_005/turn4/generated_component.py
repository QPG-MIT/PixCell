import gdsfactory as gf

@gf.cell
def create_device():
    """
    Creates a cross shape that resembles a four-petal flower.

    This is achieved by programmatically placing and rotating the
    primitive shapes (one ellipse for the petal body, one rectangle for the stem)
    four times within a parent component, and then flattening the result to
    perform a boolean union.
    """
    c = gf.Component()

    # --- Part 1: Define Parameters from Footprint and Image Analysis ---
    target_layer = (1, 0)
    footprint_size = 4.7
    stem_width = 0.4
    petal_max_width = 2.4
    
    # Distance from center to where the curved petal part ends.
    petal_tip_distance = 1.95
    
    # --- Part 2: Calculate dependent geometry values ---
    total_arm_length = footprint_size / 2
    stem_length = total_arm_length - petal_tip_distance

    # --- Part 3: Define the primitive shapes that will be reused ---
    
    # The petal body is a single ellipse. All four petals will be references
    # to this one component.
    petal_body = gf.components.ellipse(
        radii=(petal_max_width / 2, petal_tip_distance),
        layer=target_layer,
    )
    
    # The stem is a single rectangle. All four stems will be references
    # to this one component.
    stem = gf.components.rectangle(
        size=(stem_width, stem_length), layer=target_layer
    )

    # --- Part 4: Assemble the device by adding and transforming references ---
    
    # Loop to create the four arms of the cross.
    for angle in [0, 90, 180, 270]:
        # Create a temporary component to group one petal and one stem.
        # This makes applying the final rotation easier.
        arm = gf.Component()
        arm << petal_body  # Petal body is centered at (0,0)
        stem_ref = arm << stem
        
        # Position the stem's reference to sit at the tip of the petal.
        # Its center is moved to the petal's edge plus half its own length.
        stem_ref.movey(petal_tip_distance + stem_length / 2)
        
        # Add the assembled arm to the main component and rotate it.
        arm_ref = c << arm
        arm_ref.rotate(angle)

    # --- Part 5: Flatten the final component ---
    # The flatten operation performs a boolean union on all overlapping
    # shapes on the same layer, creating a new component with a single polygon.
    final_device = c.flatten()
    
    # The decorated function must return a Component object.
    return final_device

# --- Main execution block ---
if __name__ == "__main__":
    device_to_save = create_device()
    device_to_save.write_gds("device.gds")
    # device_to_save.show()