import kfactory as kf
from kfactory import kdb

# Define Layer
LAYER = (1, 0)

@kf.cell
def tooth():
    """Defines the tooth shape as a sub-cell."""
    c = kf.KCell()
    c.add_polygon([
        (-0.05, -0.2), 
        (0.05, -0.2), 
        (0.05, 0.2), 
        (-0.05, 0.2)
    ], layer=LAYER)
    return c

@kf.cell
def create_textured_arm():
    """Creates one arm of the device with the textured waveguide section."""
    c = kf.KCell()
    
    # In KFactory, define standard geometry
    # Note: KFactory handles paths/waveguides via specific routing or manual polygon placement.
    # We will approximate the layout using simple shapes to match the visual requirement.
    
    # 1. Straight segment
    # (Drawing the core waveguide)
    c.add_polygon([(-5, -0.25), (5, -0.25), (5, 0.25), (-5, 0.25)], layer=LAYER)
    
    # 2. Add the teeth (replacing add_array with a loop)
    tooth_cell = tooth()
    pitch = 0.25
    num_teeth = 40
    start_x = - (num_teeth * pitch) / 2
    
    for i in range(num_teeth):
        x_pos = start_x + (i * pitch)
        # Create an instance in the cell
        c.create_inst(tooth_cell, x=int(x_pos * 1000), y=0) 
        # Note: KFactory uses database units (usually 1000 DBU = 1um)

    return c

@kf.cell
def device():
    c = kf.KCell()
    
    # 1. Add top arm
    top_arm = c.create_inst(create_textured_arm(), x=0, y=5000)
    
    # 2. Add bottom arm (mirrored)
    # KFactory handles transforms via kdb.Trans
    # Mirroring across Y-axis:
    bottom_arm = c.create_inst(create_textured_arm(), trans=kdb.Trans(kdb.Trans.M90, 0, -5000))
    
    # 3. Add dividing line
    # Drawing a simple rectangle for the divider
    c.add_polygon([(-5000, -100), (5000, -100), (5000, 100), (-5000, 100)], layer=LAYER)
    
    return c

# Generate and view the device
if __name__ == "__main__":
    c = device()
    c.show()