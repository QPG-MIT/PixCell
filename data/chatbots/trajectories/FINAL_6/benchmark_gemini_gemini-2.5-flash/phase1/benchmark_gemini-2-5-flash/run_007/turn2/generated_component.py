import gdsfactory as gf
from typing import Callable

@gf.cell
def create_cross_shape(
    arm_half_length: float = 2.35,  # Total length of one arm from center to tip (4.7 / 2)
    width_at_center: float = 0.2,   # Width of the arm at the cross's center
    width_at_peak: float = 1.2,     # Maximum width of the petal-like arm
    peak_position_ratio: float = 0.3, # Relative position (0 to 1) of the peak width along the arm
    width_at_tip: float = 0.2,      # Width of the arm at its flat tip
    layer: tuple = (1, 0)
) -> gf.Component:
    """
    Creates a cross shape composed of four petal-like arms with flat tips.
    The arms are defined by a varying width profile along a straight path.

    Args:
        arm_half_length: Total length of one arm from the center of the cross to its outer tip.
                         Derived from footprint: 4.7 / 2 = 2.35.
        width_at_center: The width of the arm at the exact center of the cross (s=0).
                         Visual estimation from image: narrow to create a bottleneck.
        width_at_peak: The maximum width of the petal-like arm.
                       Visual estimation from image: wider than center/tip.
        peak_position_ratio: A value between 0 and 1 indicating where the maximum width occurs
                             along the arm's length (0=center, 1=tip).
                             Visual estimation from image: closer to center, e.g., 0.3-0.4.
        width_at_tip: The width of the flat rectangular tip of the arm (s=1).
                      Visual estimation from image: narrow, same as width_at_center, to make it look like a rectangular end.
        layer: GDS layer for the component (e.g., (1, 0)).

    Returns:
        A gdsfactory Component representing the complete cross shape.

    The total footprint will be (2 * arm_half_length) x (2 * arm_half_length).
    For the given parameters: 2 * 2.35 = 4.7 um.
    """
    c = gf.Component("cross_shape")

    # 1. Define the width profile for a single arm (from center to tip along a path)
    def width_profile_function(s: float) -> float:
        """
        Defines the width of a single arm as a function of normalized arclength 's'.
        's' ranges from 0 (at the center of the cross) to 1 (at the outer tip of the arm).
        The width transitions linearly from `width_at_center` to `width_at_peak`,
        and then linearly from `width_at_peak` to `width_at_tip`.
        """
        if not (0 <= s <= 1):
            raise ValueError(f"Normalized arclength 's' ({s}) must be between 0 and 1.")

        if s <= peak_position_ratio:
            # Linear interpolation from width_at_center to width_at_peak
            # Scale 's' to [0, 1] for this segment
            scaled_s = s / peak_position_ratio if peak_position_ratio > 0 else 0
            return width_at_center + (width_at_peak - width_at_center) * scaled_s
        else:
            # Linear interpolation from width_at_peak to width_at_tip
            # Scale 's' to [0, 1] for this segment
            scaled_s = (s - peak_position_ratio) / (1 - peak_position_ratio) if (1 - peak_position_ratio) > 0 else 0
            return width_at_peak + (width_at_tip - width_at_peak) * scaled_s

    # FIX: Use the gf.cross_section.cross_section factory function
    # It correctly handles passing a callable for 'width' and the 'layer'.
    xs_arm = gf.cross_section.cross_section(width=width_profile_function, layer=layer)

    # 3. Define the centerline path for a single arm, starting at (0,0) and extending upwards
    # This path represents half of the arm length, from the cross center to the tip.
    path_arm = gf.Path()
    path_arm.append(gf.path.straight(length=arm_half_length))

    # 4. Extrude the path with the varying cross-section to create one petal-shaped arm component
    # This component is 'uncentered' because its base is at (0,0) and it extends in +Y.
    petal_arm_uncentered = gf.path.extrude(path_arm, cross_section=xs_arm)

    # 5. Create a new Component to represent the single arm, centered for rotation.
    # The 'petal_arm_uncentered' extends from y=0 to y=arm_half_length.
    # To center its intended rotation pivot (which is the center of the cross) at (0,0),
    # we need to translate it downwards by `arm_half_length / 2`.
    # This centers the entire structure's bounding box around (0,0) for the final cross assembly.
    petal_arm_centered = gf.Component("petal_arm_centered_primitive")
    arm_ref_in_centered = petal_arm_centered << petal_arm_uncentered
    arm_ref_in_centered.movey(-arm_half_length / 2) # Shift down to center around (0,0)

    # 6. Add four instances of this 'petal_arm_centered' component to the main component 'c',
    # rotating each instance by 90-degree increments around (0,0) to form the cross.
    c.add_ref(petal_arm_centered) # First arm (0 degrees, pointing up)

    arm_right = c.add_ref(petal_arm_centered)
    arm_right.rotate(angle=90) # Second arm (90 degrees, pointing right)

    arm_down = c.add_ref(petal_arm_centered)
    arm_down.rotate(angle=180) # Third arm (180 degrees, pointing down)

    arm_left = c.add_ref(petal_arm_centered)
    arm_left.rotate(angle=270) # Fourth arm (270 degrees, pointing left)

    return c

# Define parameters based on the image and footprint constraint.
# Footprint is [4.7, 4.7], so arm_half_length = 4.7 / 2 = 2.35.
component = create_cross_shape(
    arm_half_length=2.35,
    width_at_center=0.2,       # Narrowest point at the cross's center
    width_at_peak=1.2,         # Widest point of the petal
    peak_position_ratio=0.3,   # Peak width occurs closer to the center (e.g., 30% along the arm)
    width_at_tip=0.2,          # Width of the flat tip
    layer=(1, 0)
)

# Verify the footprint
expected_footprint_x = 4.7
expected_footprint_y = 4.7
actual_footprint_x = component.xsize
actual_footprint_y = component.ysize

print(f"Calculated Footprint X: {actual_footprint_x:.3f} um")
print(f"Calculated Footprint Y: {actual_footprint_y:.3f} um")
print(f"Expected Footprint X: {expected_footprint_x:.3f} um")
print(f"Expected Footprint Y: {expected_footprint_y:.3f} um")

# Assert that the footprint matches the constraint
assert abs(actual_footprint_x - expected_footprint_x) < 1e-9, f"Footprint X mismatch: {actual_footprint_x} vs {expected_footprint_x}"
assert abs(actual_footprint_y - expected_footprint_y) < 1e-9, f"Footprint Y mismatch: {actual_footprint_y} vs {expected_footprint_y}"

# Save the GDS file and visualize it
component.write_gds("cross_shape.gds")
gf.show(component)