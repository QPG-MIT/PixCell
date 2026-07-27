"""Three-Group Waveguide Array Coupler - Recreation from device_bw.png"""
import gdsfactory as gf

# Top-level tunables - function-defining parameters
# Device is 120 μm wide × 4 μm tall (horizontal orientation)
# Three vertically-stacked groups
waveguide_width = 0.22      # Width of each parallel waveguide in the center section
waveguide_gap = 0.11        # Gap between parallel waveguides
num_waveguides_per_group = 5  # Number of parallel waveguides in each group's center
num_groups = 3              # Three groups vertically stacked
group_gap = 0.2             # Vertical gap between groups

# Horizontal sections
left_bundle_length = 22.0   # Length of left solid bundled region
left_fan_length = 13.0      # Length of left fan-out transition
center_parallel_length = 35.0  # Length of parallel coupling region
right_fan_length = 13.0     # Length of right fan-in transition
right_bundle_length = 37.0  # Length of right solid bundled region

# Bundle dimensions
bundle_width = 0.65         # Vertical extent of each bundled region

@gf.cell
def three_group_coupler():
    c = gf.Component("three_group_coupler")
    layer = (1, 0)

    # Calculate vertical positions for the three groups
    single_group_height = num_waveguides_per_group * waveguide_width + (num_waveguides_per_group - 1) * waveguide_gap
    total_height = num_groups * bundle_width + (num_groups - 1) * group_gap

    group_y_centers = []
    for g in range(num_groups):
        y = -total_height / 2 + g * (bundle_width + group_gap) + bundle_width / 2
        group_y_centers.append(y)

    # X positions for each section
    x_left_bundle = 0
    x_left_fan = x_left_bundle + left_bundle_length
    x_center = x_left_fan + left_fan_length
    x_right_fan = x_center + center_parallel_length
    x_right_bundle = x_right_fan + right_fan_length

    # Create each of the three groups
    for group_idx, group_y in enumerate(group_y_centers):
        # Left bundled region
        left_bundle = c << gf.components.rectangle(
            size=(left_bundle_length, bundle_width),
            layer=layer
        )
        left_bundle.xmin = x_left_bundle
        left_bundle.y = group_y

        # Left fan-out region (bundle to parallel waveguides)
        # Calculate waveguide positions within this group
        wg_y_positions = []
        for i in range(num_waveguides_per_group):
            wg_y = group_y - single_group_height / 2 + i * (waveguide_width + waveguide_gap) + waveguide_width / 2
            wg_y_positions.append(wg_y)

        for wg_idx, wg_y in enumerate(wg_y_positions):
            # Left fan taper (from bundle edge to center waveguide)
            left_taper = c << gf.components.taper(
                length=left_fan_length,
                width1=waveguide_width,
                width2=waveguide_width,
                layer=layer
            )
            left_taper.xmin = x_left_fan
            left_taper.y = wg_y

            # Center parallel waveguide
            center_wg = c << gf.components.rectangle(
                size=(center_parallel_length, waveguide_width),
                layer=layer
            )
            center_wg.xmin = x_center
            center_wg.y = wg_y

            # Right fan taper (from center waveguide to bundle edge)
            right_taper = c << gf.components.taper(
                length=right_fan_length,
                width1=waveguide_width,
                width2=waveguide_width,
                layer=layer
            )
            right_taper.xmin = x_right_fan
            right_taper.y = wg_y

        # Right bundled region
        right_bundle = c << gf.components.rectangle(
            size=(right_bundle_length, bundle_width),
            layer=layer
        )
        right_bundle.xmin = x_right_bundle
        right_bundle.y = group_y

    return c

if __name__ == "__main__":
    c = three_group_coupler()
    c.write_gds("experiments/paper_swap/final8/output/recreation_sonnet45m/device.gds")
