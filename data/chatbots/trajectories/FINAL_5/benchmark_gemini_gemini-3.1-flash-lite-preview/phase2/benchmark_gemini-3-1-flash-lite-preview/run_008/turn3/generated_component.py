import gdsfactory as gf

# FIX: Define the cross-section with the intended radius. 
# This sets the property correctly within the object.
xs = gf.cross_section.cross_section(
    width=0.5, 
    layer=(1, 0), 
    radius=2.0  # This sets the minimum allowed radius for this cross-section
)

@gf.cell
def grating_arm(length=14.0):
    """Creates one U-shaped arm with fingers."""
    c = gf.Component()
    
    # 1. Bend and Straight
    # The U-bend
    bend = c << gf.components.bend_euler(radius=2.0, angle=180, cross_section=xs)
    
    # The straight section (aligning to bend output)
    straight = c << gf.components.straight(length=length, cross_section=xs)
    straight.move((0, 4.0)) # Bend exit is at 2 * radius = 4.0
    
    # The tapered tip
    taper = c << gf.components.taper(length=1.0, width1=0.5, width2=0.05, cross_section=xs)
    taper.move((length, 4.0))

    # 2. Add Periodic Fingers
    finger_template = gf.components.rectangle(size=(0.04, 0.4), layer=(1, 0))
    
    num_fingers = 35
    spacing = length / num_fingers
    
    for i in range(num_fingers):
        f = c << finger_template
        # Place fingers on the straight section, pointing inward
        # Spine y-position is 4.0, so fingers at 4.0 - 0.45
        f.move((i * spacing + 0.2, 3.55))
        
    return c

@gf.cell
def main_device():
    c = gf.Component()
    
    # 1. Central Backbone (Manual Rectangle)
    spine = c << gf.components.rectangle(size=(18.24, 0.5), layer=(1, 0))
    
    # 2. Top Arm
    top = c << grating_arm(length=14.0)
    top.move((2.0, 0.7)) # Offset to sit above spine
    
    # 3. Bottom Arm
    # Mirror and move into position below
    bottom = c << grating_arm(length=14.0)
    bottom.mirror_y()
    bottom.move((2.0, -0.7)) 
    
    return c

if __name__ == "__main__":
    device = main_device()
    device.write_gds("final_design.gds")
    print("Geometry generated successfully.")