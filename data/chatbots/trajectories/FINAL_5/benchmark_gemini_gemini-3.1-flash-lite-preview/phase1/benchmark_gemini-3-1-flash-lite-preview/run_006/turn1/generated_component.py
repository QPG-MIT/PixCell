import gdsfactory as gf
import os

@gf.cell
def directional_coupler_fixed():
    """
    Recreation of the directional coupler using a custom cross_section
    to support tighter bend radii.
    """
    c = gf.Component("my_directional_coupler")
    
    # 1. Define custom cross_section with radius constraints
    # Setting radius and radius_min to 5 to allow the compact 5um bends
    xs = gf.cross_section.cross_section(
        width=0.5, 
        layer=(1, 0), 
        radius=5, 
        radius_min=5
    )
    
    # 2. Central coupling region
    # gap=0.2 is the distance between waveguides
    coupler = c << gf.components.coupler_straight(length=10, gap=0.2, cross_section=xs)
    
    # 3. Create bend and taper templates
    bend = gf.components.bend_euler(radius=5, angle=90, cross_section=xs)
    taper = gf.components.taper(length=10, width1=0.5, width2=1.0)
    
    # 4. Attach Bends and Tapers to the 4 ports of the coupler
    # Coupler ports: o1, o2 (left), o3, o4 (right)
    port_map = ["o1", "o2", "o3", "o4"]
    
    for port_name in port_map:
        # Create references
        b = c << bend
        t = c << taper
        
        # Connect: Coupler -> Bend -> Taper
        b.connect("o1", coupler.ports[port_name])
        t.connect("o1", b.ports["o2"])
        
        # Expose the final port
        c.add_port(f"port_{port_name}", port=t.ports["o2"])
        
    return c

# Generate the component
device = directional_coupler_fixed()

# Explicitly save the GDS file
save_path = "directional_coupler.gds"
device.write_gds(save_path)

# Confirmation
print(f"Success! GDS file generated at: {os.path.abspath(save_path)}")

# Optional: Visualize if a GUI environment is available
# device.show()