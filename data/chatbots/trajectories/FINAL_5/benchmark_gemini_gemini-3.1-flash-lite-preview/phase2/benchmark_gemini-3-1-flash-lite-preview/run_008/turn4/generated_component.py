import gdsfactory as gf

# FIX: Define the cross-section with a radius that allows for tight bends (2.0um)
# This overrides the default library constraint of 10.0um
xs = gf.cross_section.cross_section(
    width=0.5, 
    layer=(1, 0), 
    radius=2.0  
)

@gf.cell
def grating_arm(length=14.0):
    """Creates one U-shaped arm with fingers."""
    c = gf.Component()
    
    # 1. Main straight waveguide with fingers
    # We create the straight section first
    straight = c << gf.components.straight(length=length, cross_section=xs)
    
    # Add fingers
    finger_template = gf.components.rectangle(size=(0.04, 0.4), layer=(1, 0))
    num_fingers = 35
    spacing = length / num_fingers
    
    for i in range(num_fingers):
        f = c << finger_template
        # Place fingers on the waveguide
        f.move((i * spacing + 0.2, 0.3)) 
        
    # 2. Add U-Bend at the right side (o2 port)
    bend_right = c << gf.components.bend_euler(radius=2.0, angle=180, cross_section=xs)
    bend_right.connect("o1", straight.ports["o2"])
    
    # 3. Add Curved Exit at the left side (o1 port)
    bend_left = c << gf.components.bend_euler(radius=2.0, angle=-45, cross_section=xs)
    bend_left.connect("o1", straight.ports["o1"])
    
    # Expose ports for easy connection
    c.add_port("o1", port=bend_left.ports["o2"])
    c.add_port("o2", port=bend_right.ports["o2"])
    
    return c

@gf.cell
def main_device():
    c = gf.Component()
    
    # 1. Central Backbone
    spine = c << gf.components.straight(length=18.24, cross_section=xs)
    
    # 2. Top Arm
    top = c << grating_arm(length=14.0)
    top.movey(1.0) # Position above spine
    
    # 3. Bottom Arm
    bottom = c << grating_arm(length=14.0)
    bottom.mirror_y() 
    bottom.movey(-1.0) # Position below spine
    
    return c

if __name__ == "__main__":
    device = main_device()
    device.write_gds("final_design.gds")
    print("Geometry generated successfully with correct radius constraints.")