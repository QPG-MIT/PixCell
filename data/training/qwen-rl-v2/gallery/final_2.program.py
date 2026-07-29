import gdsfactory as gf

@gf.cell
def device():
    c = gf.Component()
    
    # The silhouette shows:
    # - A main rectangular body (centered at origin in y)
    # - 4 vertical prongs extending upward from the top surface
    # - 1 vertical prong extending downward from the bottom center
    # 
    # Footprint: 25um width x 10um height total
    
    # Key dimensions:
    # Total height = 10 um
    # Let body span from y=-2.5 to y=2.5 (height 5um)
    # Then prongs extend symmetrically: +3.0 up, +2.0 down from body edges? 
    # Actually: 5 (body) + a (top extension) + b (bottom extension) = 10
    # So: a + b = 5
    
    # Looking at proportions visually:
    # Top prongs appear longer than bottom prong
    # Let bottom prong extend 1.5um down, top prongs extend 5.0-1.5=3.5um up
    # Check: 5 + 3.5 + 1.5 = 10.0 ✓
    
    body_height = 5.0
    top_extension = 3.5
    bottom_extension = 1.5
    
    # Width and layout:
    body_width = 25.0
    
    # 4 prongs on top, evenly spaced
    prong_width = 2.0
    # 4 prongs with 3 gaps between them
    # Prong centers at: -7.5, -2.5, 2.5, 7.5 (centered around 0)
    prong_centers = [-7.5, -2.5, 2.5, 7.5]
    
    # Body centered at origin
    body = gf.components.rectangle(
        size=(body_width, body_height),
        layer=(1, 0),
        centered=True
    )
    body_ref = c << body
    
    # Bottom prong - centered at bottom of body, pointing down
    bottom_prong = gf.components.rectangle(
        size=(4.0, bottom_extension),
        layer=(1, 0),
        centered=False
    )
    bottom_ref = c << bottom_prong
    # Position: bottom prong's top should align with body's bottom
    # Body bottom: y = -2.5
    # Bottom prong needs to extend from y=-2.5 to y=-2.5-1.5=-4.0
    bottom_ref.move((0 - 2.0, -2.5))
    
    # Top prongs - extend upward from top of body
    for cx in prong_centers:
        top_prong = gf.components.rectangle(
            size=(prong_width, top_extension),
            layer=(1, 0),
            centered=False
        )
        top_ref = c << top_prong
        # Top prong should start at body top (y=2.5) and extend up to y=2.5+3.5=6.0
        top_ref.move((cx - prong_width/2, 2.5))
    
    return c

if __name__ == "__main__":
    device().write_gds("device.gds")