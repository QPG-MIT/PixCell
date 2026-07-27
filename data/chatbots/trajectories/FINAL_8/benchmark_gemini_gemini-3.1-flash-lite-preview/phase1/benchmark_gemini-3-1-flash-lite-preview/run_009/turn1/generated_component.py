import gdsfactory as gf
import numpy as np

@gf.cell
def custom_grating_structure():
    """
    Recreates the periodic waveguide structure using parametric primitives.
    """
    c = gf.Component()
    layer = (1, 0)
    
    # Parameters to fit the ~120um x ~4um footprint
    device_width = 110.0
    num_horizontal_lines = 5
    num_ribs = 24
    
    # 1. Create Central Horizontal Stripes
    for i in range(num_horizontal_lines):
        y_offset = (i - 2) * 0.45
        stripe = c << gf.components.rectangle(
            size=(device_width, 0.3), 
            layer=layer, 
            centered=True
        )
        stripe.movey(y_offset)
        
    # 2. Create Vertical Ribs (Top and Bottom)
    # Ribs are placed with varying heights to create the curved silhouette
    x_positions = np.linspace(-50, 50, num_ribs)
    
    for x in x_positions:
        # Calculate height: Parabolic envelope
        h = 0.5 + 0.9 * (1 - (x / 55)**2)
        
        # Top rib
        top_rib = c << gf.components.rectangle(
            size=(2.0, h), 
            layer=layer, 
            centered=True
        )
        top_rib.movex(x)
        top_rib.movey(1.5) # Offset to sit just above central stripes
        
        # Bottom rib (Mirror)
        bot_rib = c << gf.components.rectangle(
            size=(2.0, h), 
            layer=layer, 
            centered=True
        )
        bot_rib.movex(x)
        bot_rib.movey(-1.5) # Offset to sit just below central stripes
        
    return c

if __name__ == "__main__":
    device = custom_grating_structure()
    
    # CORRECTED: Use attributes of the DBox object instead of subscripting
    bbox = device.bbox()
    width = bbox.xmax - bbox.xmin
    height = bbox.ymax - bbox.ymin
    
    print(f"Device footprint: {width:.2f}um x {height:.2f}um")
    
    # device.show() # Uncomment to visualize