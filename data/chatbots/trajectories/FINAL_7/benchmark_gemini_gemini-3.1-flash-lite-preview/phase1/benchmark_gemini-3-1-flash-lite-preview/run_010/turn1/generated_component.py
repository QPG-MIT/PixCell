import gdsfactory as gf

@gf.cell
def custom_device():
    # We define the layer explicitly
    layer = (1, 0)
    c = gf.Component()

    # 1. Construct the outer ring shell using two ellipses
    # This creates a "racetrack" or stadium shape without using routing functions
    outer_ellipse = c << gf.components.ellipse(radii=(4.0, 2.0), layer=layer)
    inner_ellipse = c << gf.components.ellipse(radii=(3.4, 1.4), layer=layer)
    
    # We use boolean 'not' to create the hollow ring structure
    ring = gf.boolean(outer_ellipse, inner_ellipse, operation="not", layer=layer)
    
    # 2. Construct the two internal bars
    bar1 = c << gf.components.rectangle(size=(1.5, 0.4), layer=layer, centered=True)
    bar1.movey(0.7)
    
    bar2 = c << gf.components.rectangle(size=(1.5, 0.4), layer=layer, centered=True)
    bar2.movey(-0.7)
    
    # 3. Construct the connecting bridges
    # These connect the bars to the inner wall of the ring
    bridge_top_left = c << gf.components.rectangle(size=(0.3, 0.4), layer=layer, centered=True)
    bridge_top_left.move((-0.9, 0.7))
    
    bridge_top_right = c << gf.components.rectangle(size=(0.3, 0.4), layer=layer, centered=True)
    bridge_top_right.move((0.9, 0.7))
    
    bridge_bot_left = c << gf.components.rectangle(size=(0.3, 0.4), layer=layer, centered=True)
    bridge_bot_left.move((-0.9, -0.7))
    
    bridge_bot_right = c << gf.components.rectangle(size=(0.3, 0.4), layer=layer, centered=True)
    bridge_bot_right.move((0.9, -0.7))
    
    # 4. Final Boolean Union
    # We merge all the geometric pieces into a single unified shape
    # We first collect all references into one component, then apply union
    final_device = gf.geometry.union(c, layer=layer)
    
    return final_device

if __name__ == "__main__":
    device = custom_device()
    device.write_gds("device_layout.gds")
    device.show()