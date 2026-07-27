import gdsfactory as gf

@gf.cell
def custom_coupler():
    """
    Constructs a waveguide coupler structure based on the provided footprint.
    Footprint: 120um x 4um
    
    Structure:
    - Input straight: 10um
    - S-bend transition: 40um (dx)
    - Center coupled section: 20um
    - S-bend transition: 40um (dx)
    - Output straight: 10um
    Total: 120um
    """
    c = gf.Component()
    
    # Define cross section (waveguide width 0.5um)
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))

    # Define vertical offsets for the arms
    # Total footprint height is 4um, so outer ports at y= +/- 2um
    # Coupled section at y= +/- 0.25um
    y_outer = 2.0
    y_inner = 0.25
    
    dy = y_outer - y_inner

    def build_arm(y_start, y_end):
        """Constructs one arm of the coupler."""
        
        # 1. Straight input
        wg1 = c << gf.components.straight(length=10, cross_section=xs)
        wg1.movey(y_start)
        
        # 2. S-bend inward
        # S-bend size is (dx, dy). dy must be negative to move inwards.
        bend_in = c << gf.components.bend_s(size=(40, y_end - y_start), cross_section=xs)
        bend_in.connect("o1", wg1.ports["o2"])
        
        # 3. Center straight (coupled region)
        wg_center = c << gf.components.straight(length=20, cross_section=xs)
        wg_center.connect("o1", bend_in.ports["o2"])
        
        # 4. S-bend outward
        bend_out = c << gf.components.bend_s(size=(40, y_start - y_end), cross_section=xs)
        bend_out.connect("o1", wg_center.ports["o2"])
        
        # 5. Output straight
        wg2 = c << gf.components.straight(length=10, cross_section=xs)
        wg2.connect("o1", bend_out.ports["o2"])

    # Build Top and Bottom Arms
    # Top arm moves from +2.0 to +0.25 (dy = -1.75)
    build_arm(y_outer, y_inner)
    
    # Bottom arm moves from -2.0 to -0.25 (dy = +1.75)
    build_arm(-y_outer, -y_inner)

    return c

# Generate and save the device
if __name__ == "__main__":
    coupler = custom_coupler()
    coupler.write_gds("coupler.gds")
    
    # Verify the device
    coupler.show()