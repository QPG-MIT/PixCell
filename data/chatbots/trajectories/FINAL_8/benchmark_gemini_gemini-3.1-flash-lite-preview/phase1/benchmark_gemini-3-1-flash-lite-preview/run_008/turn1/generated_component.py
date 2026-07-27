import gdsfactory as gf

@gf.cell
def flared_coupler_device():
    """
    Recreation of the flared coupler structure.
    Constructed using straight primitives and tapers with proper port connectivity.
    """
    c = gf.Component()
    
    # Global dimensions
    total_length = 120.0
    taper_length = 20.0
    straight_len = total_length - (2 * taper_length)
    
    # Parameters
    width_narrow = 0.5
    width_wide = 1.5
    pitch = 2.0  # Vertical spacing
    
    # Define a function to create the flared line (Top/Bottom)
    def add_flared_line(y_offset):
        # 1. Flare in (Wide -> Narrow)
        t1 = c << gf.components.taper(length=taper_length, width1=width_wide, width2=width_narrow)
        # 2. Straight middle
        s = c << gf.components.straight(length=straight_len, width=width_narrow)
        # 3. Flare out (Narrow -> Wide)
        t2 = c << gf.components.taper(length=taper_length, width1=width_narrow, width2=width_wide)
        
        # Connect: Port 'o2' of first taper to 'o1' of straight
        s.connect("o1", t1.ports["o2"])
        # Connect: Port 'o2' of straight to 'o1' of second taper
        t2.connect("o1", s.ports["o2"])
        
        # Move the entire assembly to the correct Y-coordinate
        # (We move the first element; the others follow due to connectivity)
        t1.movey(y_offset)

    # Define a function to create standard straight line (Middle)
    def add_straight_line(y_offset):
        s = c << gf.components.straight(length=total_length, width=width_narrow)
        s.movey(y_offset)

    # Assemble the 5 lines
    # Offsets based on pitch: [-2, -1, 0, 1, 2] * pitch
    for i in range(5):
        y_pos = (i - 2) * pitch
        if i == 0 or i == 4:
            # Top and Bottom are flared
            add_flared_line(y_pos)
        else:
            # Middle three are straight
            add_straight_line(y_pos)

    return c

# Create and write to GDS
if __name__ == "__main__":
    device = flared_coupler_device()
    device.write_gds("flared_coupler.gds")
    print(f"Device saved successfully as flared_coupler.gds")