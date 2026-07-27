import gdsfactory as gf
import numpy as np

# Tunable parameters - function-defining knobs
bus_width_um = 2.8
grating_period_um = 4.85
finger_width_um = 1.05
finger_height_um = 6.5
finger_taper_top_width_um = 2.7
port_width_um = 0.79
port_height_um = 3.2
port_taper_ratio = 1.5  # top width / bottom width

@gf.cell
def grating_coupler_device():
    """
    Grating coupler with 4 tapered fingers, bus waveguide, and tapered port.
    Layer: (1, 0) - Silicon core layer
    """
    device = gf.Component("grating_coupler")

    # 1. Create the bus waveguide (horizontal rectangular structure)
    bus_length = 25.0
    bus = gf.components.rectangle(
        size=(bus_length, bus_width_um),
        layer=(1, 0)
    )

    # 2. Create tapered fingers
    # Each finger is a trapezoid (wider at top, narrower at base)
    num_fingers = 4

    # Center the fingers around x=0, spaced by grating_period
    finger_spacing = grating_period_um
    total_span = (num_fingers - 1) * finger_spacing
    start_x = -total_span / 2.0

    for i in range(num_fingers):
        x_center = start_x + i * finger_spacing

        # Create trapezoid: wider at top, narrower at base
        finger_y_base = bus_width_um / 2.0
        finger_y_top = finger_y_base + finger_height_um

        # Create trapezoid points (counter-clockwise from bottom-left)
        half_base_w = finger_width_um / 2.0
        half_top_w = finger_taper_top_width_um / 2.0

        points = [
            (x_center - half_base_w, finger_y_base),      # bottom-left
            (x_center + half_base_w, finger_y_base),      # bottom-right
            (x_center + half_top_w, finger_y_top),        # top-right
            (x_center - half_top_w, finger_y_top),        # top-left
        ]

        # Add trapezoid as polygon directly to device
        device.add_polygon(points, layer=(1, 0))

    # 3. Create tapered access port at the bottom
    # Port is centered, tapers from narrow at bottom to wider upward
    port_y_bottom = -port_height_um
    port_y_top = 0
    half_port_bottom = port_width_um / 2.0
    half_port_top = (port_width_um * port_taper_ratio) / 2.0

    port_points = [
        (-half_port_bottom, port_y_bottom),      # bottom-left
        (half_port_bottom, port_y_bottom),       # bottom-right
        (half_port_top, port_y_top),             # top-right
        (-half_port_top, port_y_top),            # top-left
    ]
    device.add_polygon(port_points, layer=(1, 0))

    # 4. Add bus at origin (centered vertically)
    bus_ref = device.add_ref(bus)
    bus_ref.move((-bus_length / 2.0, -bus_width_um / 2.0))

    return device


if __name__ == "__main__":
    import os
    c = grating_coupler_device()
    c.show()
    script_dir = os.path.dirname(os.path.abspath(__file__))
    gds_path = os.path.join(script_dir, "device.gds")
    c.write_gds(gds_path)
    print(f"Device written to {gds_path}")
