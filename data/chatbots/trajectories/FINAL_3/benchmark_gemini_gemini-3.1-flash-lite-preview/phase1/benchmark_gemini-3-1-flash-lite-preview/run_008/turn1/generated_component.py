import gdsfactory as gf

@gf.cell
def flared_coupler_device():
    """
    Constructs the flared waveguide coupler by assembling 
    straight and S-bend components.
    """
    c = gf.Component("flared_coupler")
    
    # Define cross section
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # We will build two symmetric arms.
    # Total length is 120um. We break each arm into 5 segments:
    # [Straight 20um] -> [S-bend 20um] -> [Straight 40um] -> [S-bend 20um] -> [Straight 20um]
    
    def build_arm(y_offset_sign=1):
        # Determine y-shift for the S-bend (0.5um total offset)
        # Note: If sign is 1 (top arm), we move down (-0.5) to reach center
        y_shift = 0.5 * -y_offset_sign
        
        # 1. Left input
        start_wg = c << gf.components.straight(length=20, cross_section=xs)
        
        # 2. Transition to center (S-bend)
        # size=(dx, dy). dx=20, dy=y_shift
        bend_in = c << gf.components.bend_s(size=(20, y_shift), cross_section=xs)
        
        # 3. Center coupling section
        center_wg = c << gf.components.straight(length=40, cross_section=xs)
        
        # 4. Transition back to output (S-bend)
        bend_out = c << gf.components.bend_s(size=(20, -y_shift), cross_section=xs)
        
        # 5. Right output
        end_wg = c << gf.components.straight(length=20, cross_section=xs)
        
        # Connect everything
        bend_in.connect("o1", start_wg.ports["o2"])
        center_wg.connect("o1", bend_in.ports["o2"])
        bend_out.connect("o1", center_wg.ports["o2"])
        end_wg.connect("o1", bend_out.ports["o2"])
        
        return start_wg, end_wg

    # Build Top Arm (y=0.5)
    build_arm(y_offset_sign=1)
    
    # Build Bottom Arm (y=-0.5)
    build_arm(y_offset_sign=-1)
    
    return c

# Generate and save
if __name__ == "__main__":
    device = flared_coupler_device()
    # Save the GDS file
    device.write_gds("flared_coupler.gds")
    # Open in KLayout
    device.show()