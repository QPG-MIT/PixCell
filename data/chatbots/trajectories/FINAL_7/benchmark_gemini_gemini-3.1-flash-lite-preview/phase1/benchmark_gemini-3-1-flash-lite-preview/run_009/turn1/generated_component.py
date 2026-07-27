import gdsfactory as gf

@gf.cell
def custom_device():
    """
    Recreates the device geometry:
    - Outer Racetrack Loop
    - Two inner rectangular structures
    - Connecting bars
    """
    c = gf.Component()
    
    # Define a cross-section for the outer loop (width of the racetrack line)
    xs = gf.cross_section.cross_section(width=0.4, layer=(1, 0))

    # --- 1. Outer Racetrack Loop ---
    # Goal: Fit within 3.0 x 5.5
    # Parameters for the path
    radius = 1.0  # Bend radius
    # Racetrack length = 5.5 (total) - 2 * radius (top/bottom) = 3.5
    straight_length = 3.5 
    
    p = gf.Path()
    p.append(gf.path.straight(length=straight_length))
    p.append(gf.path.arc(radius=radius, angle=180))
    p.append(gf.path.straight(length=straight_length))
    p.append(gf.path.arc(radius=radius, angle=180))
    
    # Extrude path to create the outer loop
    racetrack = gf.path.extrude(p, cross_section=xs)
    
    # --- 2. Inner Structures (Rectangles + Connectors) ---
    # Inner rectangular blocks
    rect_inner = gf.components.rectangle(size=(1.6, 1.0), layer=(1, 0), centered=True)
    
    # Connecting bars (rectangles)
    bar = gf.components.rectangle(size=(2.2, 0.4), layer=(1, 0), centered=True)
    
    # --- 3. Assembly and Boolean Union ---
    # Add all parts to the component
    ref_ring = c << racetrack
    
    # Place two inner rectangles separated vertically
    r1 = c << rect_inner
    r1.movey(0.7)
    
    r2 = c << rect_inner
    r2.movey(-0.7)
    
    # Place connectors
    b1 = c << bar
    b1.movey(0.7)
    
    b2 = c << bar
    b2.movey(-0.7)
    
    # Flatten everything into a single union polygon
    # This ensures the separate parts become one solid geometric object
    final_shape = gf.boolean(c, c, operation="or", layer=(1, 0))
    
    # Create final component from the union
    final_c = gf.Component("final_device")
    final_c.add_ref(final_shape)
    
    return final_c

# Generate the device
device = custom_device()

# Save the GDSII file
device.write_gds("device.gds")