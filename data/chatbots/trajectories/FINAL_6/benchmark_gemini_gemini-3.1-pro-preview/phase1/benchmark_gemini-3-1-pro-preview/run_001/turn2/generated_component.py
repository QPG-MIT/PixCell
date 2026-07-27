import gdsfactory as gf

@gf.cell
def petal_cross_device():
    # 1. Create the main petal body using two crossed ellipses.
    # Radii adjusted to make the curved sections slightly shorter and slightly thinner,
    # allowing more room for the prominent straight tips.
    ellipse_h = gf.components.ellipse(radii=(2.0, 0.55), layer=(1, 0))
    ellipse_v = gf.components.ellipse(radii=(0.55, 2.0), layer=(1, 0))
    
    # Union the ellipses into a single central core shape
    core = gf.boolean(ellipse_h, ellipse_v, operation="or", layer=(1, 0))
    
    # 2. Create the straight tips
    # Length increased to 0.7 to ensure they embed deeply and expose a longer straight section.
    rect_h = gf.components.rectangle(size=(0.7, 0.2), layer=(1, 0), centered=True)
    rect_v = gf.components.rectangle(size=(0.2, 0.7), layer=(1, 0), centered=True)
    
    # Create a temporary component to hold and position all 4 tips
    tips = gf.Component()
    
    # Position tips. Centering a 0.7-long rect at 2.0 means it spans [1.65, 2.35].
    # This perfectly achieves the target total footprint of 4.7 (2.35 * 2).
    r_right = tips << rect_h
    r_right.move((2.0, 0))
    
    r_left = tips << rect_h
    r_left.move((-2.0, 0))
    
    r_top = tips << rect_v
    r_top.move((0, 2.0))
    
    r_bottom = tips << rect_v
    r_bottom.move((0, -2.0))
    
    # 3. Final Assembly
    # Boolean union the core with the tips
    final_device = gf.boolean(core, tips, operation="or", layer=(1, 0))
    
    return final_device

if __name__ == "__main__":
    # Create the component
    c = petal_cross_device()
    
    # Save the component to a GDS file
    c.write_gds("petal_cross_device.gds")