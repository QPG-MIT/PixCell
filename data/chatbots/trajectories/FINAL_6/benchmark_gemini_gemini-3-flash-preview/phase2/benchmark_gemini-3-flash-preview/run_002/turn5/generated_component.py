import gdsfactory as gf
import math

@gf.cell
def recreated_device_v7():
    """
    Fixed and refined organic four-petal device for Turn 6.
    - Corrected TypeError by removing 'npoints' from gf.components.circle.
    - Uses a parametric sine-wave envelope for high-fidelity almond-shaped petals.
    - Employs a central hub to ensure a smooth 'melted' intersection.
    - Total Footprint: 4.7um x 4.7um.
    """
    c = gf.Component("recreated_device_v7")
    layer = (1, 0)
    
    # --- 1. Dimensions for 4.7um Footprint ---
    total_radius = 2.35    # Half of 4.7um
    hub_radius = 0.5       # The radius where the petals converge
    stub_length = 0.35     # Length of the rectangular terminal tip
    petal_len = total_radius - hub_radius - stub_length # Length of the curved body
    
    # Half-widths (thickness) for the petal envelope
    base_h_width = 0.4     # Width where petal meets the hub
    stub_h_width = 0.16    # Width of the rectangular terminal stub
    max_h_width = 0.82     # Peak "fatness" of the almond petal
    
    res = 50 # Points per half-curve (high res for smoothness)
    
    # --- 2. Generate Parametric Petal Points ---
    petal_pts = []
    
    # Generate Top Curve: Hub -> Peak -> Stub Start
    for i in range(res + 1):
        t = i / res # normalized progress (0 to 1)
        x = hub_radius + t * petal_len
        
        # Linear transition for the baseline width
        y_lin = base_h_width + (stub_h_width - base_h_width) * t
        
        # Sine bulge to create the organic "belly" of the petal
        # We calculate the amplitude so the total width peaks at max_h_width
        peak_lin = (base_h_width + stub_h_width) / 2
        amplitude = max_h_width - peak_lin
        y_bulge = amplitude * math.sin(math.pi * t)
        
        petal_pts.append((x, y_lin + y_bulge))
        
    # The rectangular terminal tip
    petal_pts.append((total_radius, stub_h_width))
    petal_pts.append((total_radius, -stub_h_width))
    
    # Generate Bottom Curve (Mirrored)
    for i in range(res, -1, -1):
        t = i / res
        x = hub_radius + t * petal_len
        y_lin = base_h_width + (stub_h_width - base_h_width) * t
        peak_lin = (base_h_width + stub_h_width) / 2
        amplitude = max_h_width - peak_lin
        y_bulge = amplitude * math.sin(math.pi * t)
        
        petal_pts.append((x, -(y_lin + y_bulge)))

    # --- 3. Assembly ---
    assembly = gf.Component("assembly_temp")
    
    # Create the single petal unit
    petal_unit = gf.Component("petal_unit")
    petal_unit.add_polygon(petal_pts, layer=layer)
    
    # Add four petals at cardinal angles
    for angle in [0, 90, 180, 270]:
        ref = assembly << petal_unit
        ref.rotate(angle)
    
    # Add central circular hub to fill the core smoothly
    # Note: 'npoints' removed to fix the TypeError.
    assembly << gf.components.circle(radius=hub_radius * 1.1, layer=layer)
    
    # --- 4. Final Boolean Merge ---
    # We use boolean 'or' to remove internal lines and create one clean silhouette.
    try:
        merged = gf.boolean(A=assembly, B=assembly, operation="or", layer=layer)
        c.add_ref(merged)
    except Exception:
        # Fallback if boolean library is unavailable
        c.add_ref(assembly)

    return c

if __name__ == "__main__":
    # Generate the component
    device = recreated_device_v7()
    
    # Save to GDS file
    filename = "recreated_device_v7.gds"
    device.write_gds(filename)
    
    print(f"Success! GDS file saved as: {filename}")