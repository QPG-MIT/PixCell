import gdsfactory as gf
import os

# 1. Define the cross-section
# We define a standard waveguide cross-section
xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))

@gf.cell
def waveguide_bracket():
    """
    Creates a single 'bracket' shaped waveguide unit:
    [Upward Bend] - [Straight] - [Downward Bend]
    """
    c = gf.Component()
    
    # Create the primitives
    # Straight length
    straight_len = 50.0
    
    # 90 degree bends
    bend1 = c << gf.components.bend_euler(radius=10.0, angle=90, cross_section=xs)
    straight = c << gf.components.straight(length=straight_len, cross_section=xs)
    bend2 = c << gf.components.bend_euler(radius=10.0, angle=90, cross_section=xs)
    
    # Connect the ports
    # Connect first bend to the start of the straight
    bend1.connect("o2", straight.ports["o1"])
    # Connect second bend to the end of the straight
    bend2.connect("o1", straight.ports["o2"])
    
    # Combine into a single component with ports
    c.add_port("o1", port=bend1.ports["o1"])
    c.add_port("o2", port=bend2.ports["o2"])
    
    return c

@gf.cell
def multi_waveguide_device():
    """
    Composes 5 parallel bracket waveguides.
    """
    c = gf.Component()
    
    num_waveguides = 5
    pitch = 3.0 # Spacing between waveguides
    
    for i in range(num_waveguides):
        # Create a new unit
        wg_unit = c << waveguide_bracket()
        
        # Position them by shifting Y (pitch * index)
        # Center them around y=0
        y_pos = (i - (num_waveguides - 1) / 2) * pitch
        wg_unit.movey(y_pos)
        
    return c

# --- Execution ---
if __name__ == "__main__":
    # Create the component
    device = multi_waveguide_device()
    
    # Define file path for the output
    gds_filename = "device.gds"
    
    # Explicitly write the file
    device.write_gds(gds_filename)
    
    # Confirm output
    if os.path.exists(gds_filename):
        print(f"Success! GDS file produced: {os.path.abspath(gds_filename)}")
    else:
        print("Error: GDS file was not saved.")
        
    # Optional: Open in viewer if installed
    # device.show()