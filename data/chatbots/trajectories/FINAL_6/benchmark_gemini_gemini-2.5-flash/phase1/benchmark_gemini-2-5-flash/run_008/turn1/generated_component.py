import gdsfactory as gf
import numpy as np

@gf.cell
def custom_flower_cross() -> gf.Component:
    """
    Recreates the specified flower-cross geometry using GDSFactory's
    parametric path extrusion with a sine-shaped width transition.
    """
    c = gf.Component("flower_cross")

    # --- Parameters derived from the footprint and visual analysis ---
    total_length = 4.7  # Overall side length of the square bounding box (um)
    radius_from_center = total_length / 2  # Length of each arm from center to tip (um)

    stem_width = 0.5  # Width of the narrowest part of the arm (the "stem") (um)
    petal_max_width = 1.8  # Maximum width of the "petal" part (at the device center) (um)

    # --- 1. Define the base path for a single arm ---
    # The path starts at (0,0) and extends along the positive x-axis.
    path_segment = gf.path.straight(length=radius_from_center)

    # --- 2. Define cross-sections for the wide and narrow parts ---
    # The widest part occurs at the start of the path (x=0, center of device).
    # The narrowest part occurs at the end of the path (x=radius_from_center, tip of the arm).
    default_layer = (1, 0) # Use a common GDS layer

    xs_wide = gf.cross_section.cross_section(width=petal_max_width, layer=default_layer)
    xs_narrow = gf.cross_section.cross_section(width=stem_width, layer=default_layer)

    # --- 3. Create a transition profile ---
    # The 'sine' width_type ensures a smooth, curved tapering from wide to narrow,
    # matching the appearance of the petals in the reference image.
    transition_profile = gf.path.transition(xs_wide, xs_narrow, width_type='sine')

    # --- 4. Extrude the path with the transition to create one arm component ---
    # This component starts wide at its 'o1' port (at path start, i.e., origin)
    # and ends narrow at its 'o2' port (at path end, i.e., radius_from_center).
    one_arm_component = gf.path.extrude_transition(path_segment, transition_profile)

    # --- 5. Assemble the four arms by rotating them around the origin ---
    # GDSFactory automatically merges overlapping polygons on the same layer.
    
    # Right arm (no rotation, default orientation along +X)
    c.add_ref(one_arm_component)

    # Top arm (rotate 90 degrees)
    ref_top = c.add_ref(one_arm_component)
    ref_top.rotate(90)

    # Left arm (rotate 180 degrees)
    ref_left = c.add_ref(one_arm_component)
    ref_left.rotate(180)

    # Bottom arm (rotate 270 degrees)
    ref_bottom = c.add_ref(one_arm_component)
    ref_bottom.rotate(270)

    # The bounding box of the combined geometry will automatically be 4.7 x 4.7 um.
    return c

# --- Verification ---
# Create the component
device = custom_flower_cross()

# Get the actual bounding box dimensions.
# Based on the error, `device.bbox` is acting like a method. Call it as such:
bbox = device.bbox() # Changed from device.bbox to device.bbox()

# `bbox()` returns a numpy array like [[min_x, min_y], [max_x, max_y]]
actual_width = bbox[1][0] - bbox[0][0]
actual_height = bbox[1][1] - bbox[0][1]

# Expected dimensions from the footprint constraint
expected_width = 4.7
expected_height = 4.7

# Assert that the dimensions match the footprint constraint
# Use a small tolerance for floating point comparisons
tolerance = 1e-6 
assert abs(actual_width - expected_width) < tolerance, f"Width mismatch: Expected {expected_width}, Got {actual_width}"
assert abs(actual_height - expected_height) < tolerance, f"Height mismatch: Expected {expected_height}, Got {actual_height}"

print(f"Device successfully created with dimensions: {actual_width:.3f}um x {actual_height:.3f}um")
print(f"Footprint constraint satisfied: {expected_width}um x {expected_height}um")

# To visualize the GDS layout (requires KLayout or other GDS viewer setup)
# device.show()

# To save the GDS file
# device.write_gds("flower_cross.gds")