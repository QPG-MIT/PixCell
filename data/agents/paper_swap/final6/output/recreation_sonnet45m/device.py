"""4-port directional coupler with elliptical coupling lobes."""
import gdsfactory as gf
import numpy as np

# === TUNABLES (function-defining knobs) ===
input_width = 0.45  # Width of input/output waveguides (um)
input_length = 0.85  # Length of straight input section (um)
lobe_major = 1.5  # Major axis (length) of elliptical coupling lobe (um)
lobe_minor = 0.95  # Minor axis (width) of elliptical coupling lobe (um)

# === LAYER ===
layer = (1, 0)


@gf.cell
def four_port_coupler():
    """4-port directional coupler with elliptical coupling lobes."""
    c = gf.Component()

    # Create four elliptical coupling lobes positioned at 0°, 90°, 180°, 270°
    for angle_deg in [0, 90, 180, 270]:
        angle_rad = np.radians(angle_deg)

        # Create ellipse using gdsfactory ellipse primitive
        ellipse = gf.components.ellipse(
            radii=(lobe_major/2, lobe_minor/2),
            layer=layer
        )

        # Position ellipse - center offset by half major axis
        ellipse_ref = c.add_ref(ellipse)
        offset = lobe_major/2
        ellipse_ref.move((offset * np.cos(angle_rad), offset * np.sin(angle_rad)))

        # Add straight input waveguide extending from the ellipse
        # Calculate start position (far edge of ellipse)
        wg_start = offset + lobe_major/2
        wg_end = wg_start + input_length

        # Create rectangular waveguide
        wg_points = [
            (wg_start * np.cos(angle_rad) - input_width/2 * np.sin(angle_rad),
             wg_start * np.sin(angle_rad) + input_width/2 * np.cos(angle_rad)),
            (wg_start * np.cos(angle_rad) + input_width/2 * np.sin(angle_rad),
             wg_start * np.sin(angle_rad) - input_width/2 * np.cos(angle_rad)),
            (wg_end * np.cos(angle_rad) + input_width/2 * np.sin(angle_rad),
             wg_end * np.sin(angle_rad) - input_width/2 * np.cos(angle_rad)),
            (wg_end * np.cos(angle_rad) - input_width/2 * np.sin(angle_rad),
             wg_end * np.sin(angle_rad) + input_width/2 * np.cos(angle_rad))
        ]
        c.add_polygon(wg_points, layer=layer)

    return c


# === MAIN ===
if __name__ == "__main__":
    component = four_port_coupler()
    component.write_gds("device.gds")
    print(f"Generated device.gds")
    print(f"Tunables: input_width={input_width}, input_length={input_length}, lobe_major={lobe_major}, lobe_minor={lobe_minor}")
