import gdsfactory as gf

@gf.cell
def smooth_coupler_device():
    c = gf.Component()
    
    # 1. Define the cross-section
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))

    # 2. Use the standard coupler component
    # This automatically includes the straight section and smooth Euler transitions
    # This is the cleanest way to guarantee the geometry is perfect and efficient.
    coupler = c << gf.components.coupler(
        gap=0.2,
        length=60,
        dy=2.0,           # Vertical offset of the S-bend
        dx=30,            # Horizontal length of the S-bend
        cross_section=xs
    )

    # 3. Add ports for external connectivity
    c.add_port("o1", port=coupler.ports["o1"])
    c.add_port("o2", port=coupler.ports["o4"])
    c.add_port("o3", port=coupler.ports["o2"])
    c.add_port("o4", port=coupler.ports["o3"])

    return c

# Generate and save the device
if __name__ == "__main__":
    device = smooth_coupler_device()
    device.write_gds("smooth_coupler.gds")
    print("Device generated successfully.")
    # device.show()