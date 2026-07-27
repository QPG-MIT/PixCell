import gdsfactory as gf

@gf.cell
def custom_coupler():
    """
    Constructs a fused coupler structure with a total length of 120um.
    Uses direct port connections to ensure compatibility with different library versions.
    """
    c = gf.Component()
    
    # Define cross section
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))

    # 1. Use the built-in coupler component
    # gap=0 creates the fused section.
    c_coupler = c << gf.components.coupler(gap=0, length=40, cross_section=xs)

    # 2. Extend the ports.
    # Iterate directly over the ports in the component. 
    # Each 'port' is an object that contains its own 'name' attribute.
    for port in c_coupler.ports:
        
        # Add a 40um straight section
        wg_extension = c << gf.components.straight(length=40, cross_section=xs)
        
        # Connect the straight section directly to the port object
        # This is more robust than looking up by string name
        wg_extension.connect("o1", port)
        
        # Expose the new end as an external port on the parent component
        c.add_port(port.name, port=wg_extension.ports["o2"])

    return c

# Generate and save the device
if __name__ == "__main__":
    coupler = custom_coupler()
    coupler.write_gds("fused_coupler.gds")
    
    # Visualize to verify the geometry
    coupler.show()