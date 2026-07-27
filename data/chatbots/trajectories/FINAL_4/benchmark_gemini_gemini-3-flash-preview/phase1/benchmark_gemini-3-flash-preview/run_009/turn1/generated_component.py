import gdsfactory as gf

@gf.cell
def symmetric_curved_coupler():
    """
    Recreates the curved coupler geometry using parametric S-bend primitives.
    Total footprint: 18um x 3um.
    """
    c = gf.Component("curved_coupler")
    
    # 1. Define the cross-section
    # Based on the 3um height footprint, a 0.6um width matches the visual proportions.
    width = 0.6
    xs = gf.cross_section.cross_section(width=width, layer=(1, 0))
    
    # 2. Define geometry parameters
    total_length = 18.0
    half_length = total_length / 2  # Each S-bend covers half the total length
    vertical_dip = 0.6              # The amount each arm curves toward the center
    end_separation = 2.0            # Center-to-center distance at the ports
    
    # 3. Create the Top Arm
    # The top arm consists of one S-bend dipping down, followed by one rising back up.
    top_s1 = gf.components.bend_s(size=(half_length, -vertical_dip), cross_section=xs)
    top_s2 = gf.components.bend_s(size=(half_length, vertical_dip), cross_section=xs)
    
    # Add references and connect them
    t1 = c << top_s1
    t2 = c << top_s2
    t2.connect("o1", t1.ports["o2"])
    
    # 4. Create the Bottom Arm
    # The bottom arm mirrors the top, rising up then dropping back down.
    bot_s1 = gf.components.bend_s(size=(half_length, vertical_dip), cross_section=xs)
    bot_s2 = gf.components.bend_s(size=(half_length, -vertical_dip), cross_section=xs)
    
    # Add references and connect them
    b1 = c << bot_s1
    b2 = c << bot_s2
    b2.connect("o1", b1.ports["o2"])
    
    # 5. Position the arms
    # Move the bottom arm relative to the top arm to achieve the desired vertical spacing.
    # If t1.o1 is at (0,0), we move b1.o1 to (0, -end_separation).
    b1.movey(-end_separation)
    
    # 6. Expose ports
    c.add_port("o1", port=t1.ports["o1"])
    c.add_port("o2", port=b1.ports["o1"])
    c.add_port("o3", port=t2.ports["o2"])
    c.add_port("o4", port=b2.ports["o2"])
    
    return c

if __name__ == "__main__":
    # Create the component
    component = symmetric_curved_coupler()
    
    # Export to GDS to verify against footprint
    component.write_gds("curved_coupler.gds")
    
    # Display the component
    component.show()