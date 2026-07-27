import gdsfactory as gf

@gf.cell
def waveguide_coupler_device():
    c = gf.Component()
    
    # 1. Define the cross-section
    # Using the standard cross-section builder
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))

    # 2. Add the central coupler straight section
    # This creates the parallel waveguides in the middle
    coupler = c << gf.components.coupler_straight(length=60, gap=0.2, cross_section=xs)

    # 3. Add S-bends to create the transitions
    # We add 4 bends, one for each port of the coupler to fan out the waveguides.
    # We use bend_s(size=(dx, dy)) where dy provides the vertical offset.
    
    # Left side bends
    b1 = c << gf.components.bend_s(size=(30, 2), cross_section=xs)
    b2 = c << gf.components.bend_s(size=(30, -2), cross_section=xs)
    
    # Right side bends
    b3 = c << gf.components.bend_s(size=(30, 2), cross_section=xs)
    b4 = c << gf.components.bend_s(size=(30, -2), cross_section=xs)

    # 4. Connect the ports
    # Connect bends to the central coupler section
    b1.connect("o2", coupler.ports["o1"])
    b2.connect("o2", coupler.ports["o2"])
    b3.connect("o1", coupler.ports["o3"])
    b4.connect("o1", coupler.ports["o4"])

    # 5. Expose external ports
    c.add_port("o1", port=b1.ports["o1"])
    c.add_port("o2", port=b2.ports["o1"])
    c.add_port("o3", port=b3.ports["o2"])
    c.add_port("o4", port=b4.ports["o2"])

    return c

# Generate and save the device
if __name__ == "__main__":
    device = waveguide_coupler_device()
    device.write_gds("coupler_device.gds")
    
    # Optional: Display the device
    # device.show()