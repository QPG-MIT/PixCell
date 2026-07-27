import gdsfactory as gf

@gf.cell
def directional_coupler_final():
    """
    Recreation of the directional coupler using the parametric coupler primitive.
    """
    c = gf.Component("directional_coupler")

    # 1. Define custom cross_section
    # The radius is defined here, not in the coupler function call.
    xs = gf.cross_section.cross_section(
        width=0.5, 
        layer=(1, 0), 
        radius=5
    )
    
    # 2. Build the parametric coupler
    # The coupler function automatically builds the central straight section 
    # and the four curved arms symmetrically.
    # Note: We pass 'xs' so the bends use our specified radius.
    coupler_base = gf.components.coupler(
        length=10, 
        gap=0.2, 
        cross_section=xs
    )
    coupler_ref = c << coupler_base
    
    # 3. Add tapers to all 4 ports
    # We define a single taper template to reuse
    taper = gf.components.taper(
        length=10, 
        width1=0.5, 
        width2=1.0, 
        cross_section=xs
    )
    
    # Connect a taper to each of the 4 ports ('o1'..'o4')
    # The coupler primitive provides these ports by default.
    for port_name in ["o1", "o2", "o3", "o4"]:
        t = c << taper
        t.connect("o1", coupler_ref.ports[port_name])
        
        # Expose the new port (the end of the taper)
        c.add_port(f"port_{port_name}", port=t.ports["o2"])
        
    return c

# Generate the component
device = directional_coupler_final()

# Save the GDS file
save_path = "directional_coupler_final.gds"
device.write_gds(save_path)

print(f"Success! GDS file generated at: {save_path}")