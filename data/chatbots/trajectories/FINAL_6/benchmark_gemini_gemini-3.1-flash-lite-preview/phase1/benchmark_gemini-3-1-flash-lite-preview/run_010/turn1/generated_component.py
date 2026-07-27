import gdsfactory as gf

@gf.cell
def petal_arm():
    """
    Creates a single arm consisting of an elliptical petal and 
    a small rectangular tab.
    """
    c = gf.Component()
    
    # 1. Create the elliptical petal
    # We create it at (0,0) and move it along the x-axis
    petal = c << gf.components.ellipse(radii=(1.15, 0.6), layer=(1, 0))
    petal.movex(1.0)
    
    # 2. Create the rectangular tab
    # Place it at the tip of the petal
    tab = c << gf.components.rectangle(size=(0.4, 0.25), layer=(1, 0), centered=True)
    tab.movex(2.15)
    
    return c

@gf.cell
def cross_device():
    """
    Assembles 4 petal arms into a cross-like shape.
    """
    c = gf.Component()
    
    # Add 4 instances of the petal_arm, each rotated by 90 degrees
    # This creates the 4-fold symmetric cross shape
    for i in range(4):
        arm = c << petal_arm()
        arm.rotate(i * 90)
        
    return c

# Create and save the device
device = cross_device()

# View the device (if in Jupyter/KLayout)
# device.show() 

# Save to file
device.write_gds("cross_device.gds")