import gdsfactory as gf

@gf.cell
def mmi_1x4_splitter():
    c = gf.Component("mmi_1x4")

    # 1. Main Body
    # Create the central rectangular footprint constraint (25um x 10um)
    # centered=True places the origin (0,0) exactly at the center of the rectangle
    # so the top edge is at y = 5 and bottom edge is at y = -5
    body = c << gf.components.rectangle(size=(25, 10), centered=True)

    # 2. Top Arms (Output Ports)
    # Define a single composite arm to be arrayed
    @gf.cell
    def top_arm():
        arm = gf.Component()
        # Taper transitioning from the wider MMI body interface down to a straight width
        taper_sec = arm << gf.components.taper(length=12.0, width1=3.0, width2=0.5)
        
        # Straight section (created using a constant-width taper to avoid cross_section complexities)
        straight_sec = arm << gf.components.taper(length=15.0, width1=0.5, width2=0.5)
        
        # Connect the straight section to the end of the taper
        straight_sec.connect("o1", taper_sec.ports["o2"])
        
        # Expose the wide base as the input port of this composite sub-component
        arm.add_port("in", port=taper_sec.ports["o1"])
        return arm

    # Evenly space 4 ports across the 25 µm width
    pitch = 25.0 / 4
    # Calculate the centers of the 4 equal segments: -9.375, -3.125, 3.125, 9.375
    x_positions = [(-12.5 + pitch / 2) + i * pitch for i in range(4)]

    for x in x_positions:
        arm_ref = c << top_arm()
        # Default taper 'o1' port faces West (180 deg). 
        # Rotating +90 deg makes it face South (270 deg) to cleanly meet the top edge.
        arm_ref.rotate(90)
        # Move the newly facing "in" port to the MMI's top edge
        arm_ref.move((x, 5.0))

    # 3. Bottom Arm (Input Port)
    # A single tapered feed attached to the bottom edge
    t_bot = c << gf.components.taper(length=6.0, width1=4.0, width2=1.5)
    
    # Default taper 'o1' port faces West (180 deg).
    # Rotating -90 deg makes it face North (90 deg) to cleanly meet the bottom edge.
    t_bot.rotate(-90)
    # Move the wide base port exactly to the center bottom of the MMI body
    t_bot.move((0, -5.0))

    return c

if __name__ == "__main__":
    # Instantiate the assembled component
    device = mmi_1x4_splitter()
    
    # Write the component out to a GDS file
    device.write_gds("mmi_1x4.gds")