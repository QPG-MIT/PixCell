import gdsfactory as gf

@gf.cell
def leaf_cross_device():
    """
    Recreates the 4-lobed device geometry.
    Composition: Elliptical petals with rectangular tips.
    Footprint: 4.7um x 4.7um
    """
    layer = (1, 0)
    
    # --- Precision Dimensions ---
    # Total radius needed = 2.35um (for 4.7um width)
    # Petal major radius = 1.85um
    # Tip length = 0.5um (1.85 + 0.5 = 2.35)
    petal_rx = 1.85
    petal_ry = 0.45
    tip_l = 0.5
    tip_w = 0.2
    
    # 1. Create the Horizontal component
    horiz = gf.Component("h_base")
    # Central petal body
    horiz << gf.components.ellipse(radii=(petal_rx, petal_ry), layer=layer)
    # Right tip
    tr = horiz << gf.components.rectangle(size=(tip_l, tip_w), layer=layer, centered=True)
    tr.movex(petal_rx + tip_l/2)
    # Left tip
    tl = horiz << gf.components.rectangle(size=(tip_l, tip_w), layer=layer, centered=True)
    tl.movex(-(petal_rx + tip_l/2))

    # 2. Create the Vertical component
    vert = gf.Component("v_base")
    # Re-use the horizontal logic rotated 90 degrees
    v_ref = vert << horiz
    v_ref.rotate(90)

    # 3. Boolean OR to merge the parts into a single geometry
    # This fulfills the Parametric Construction requirement
    device = gf.boolean(A=horiz, B=vert, operation="or", layer=layer)
    device.name = "leaf_cross"
    
    return device

if __name__ == "__main__":
    # Generate the component
    component = leaf_cross_device()
    
    # --- FILE PRODUCTION ---
    # This line writes the physical GDSII file to your current directory
    filename = "leaf_cross.gds"
    component.write_gds(filename)
    
    print(f"DONE: GDS file '{filename}' has been produced.")
    print(f"Device size: {component.xsize:.2f}um x {component.ysize:.2f}um")
    
    # Optional: Open in KLayout if available
    try:
        component.show()
    except Exception:
        print("Note: 'component.show()' failed (likely no GUI environment), but the GDS file was saved.")