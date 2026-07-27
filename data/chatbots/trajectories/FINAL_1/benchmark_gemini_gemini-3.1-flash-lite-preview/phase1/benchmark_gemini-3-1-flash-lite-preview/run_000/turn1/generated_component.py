import gdsfactory as gf
import numpy as np

@gf.cell
def custom_coupler():
    """
    Constructs the Y-junction/taper structure using path-based extrusion
    to avoid rotation-related grid errors.
    """
    c = gf.Component()
    
    # 1. Central Spear (Straight Taper)
    # Using straight components is safe on-grid.
    spear = c << gf.components.taper(length=40, width1=0.4, width2=0.05)
    spear.center = (20, 0)

    # 2. Top and Bottom Arms
    # To get the "flare" without rotating a component instance, 
    # we use an Euler bend in a Path. This creates the curve 
    # parametrically without triggering off-grid errors.
    
    def create_arm(y_offset, angle_sign):
        # Create a path: Straight section + Euler bend for the flare
        p = gf.Path()
        p.append(gf.path.straight(length=10)) 
        p.append(gf.path.euler(radius=100, angle=5 * angle_sign))
        p.append(gf.path.straight(length=30))
        
        # Extrude the path into a component (this avoids Reference rotation)
        # We use a cross_section to define the width
        xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
        arm_comp = p.extrude(xs)
        
        # Add the extruded component
        arm_ref = c << arm_comp
        arm_ref.move((0, y_offset))
        return arm_ref

    # Add the arms
    create_arm(y_offset=0.6, angle_sign=1)   # Top
    create_arm(y_offset=-0.6, angle_sign=-1) # Bottom

    return c

# Generate and visualize
device = custom_coupler()
device.show()