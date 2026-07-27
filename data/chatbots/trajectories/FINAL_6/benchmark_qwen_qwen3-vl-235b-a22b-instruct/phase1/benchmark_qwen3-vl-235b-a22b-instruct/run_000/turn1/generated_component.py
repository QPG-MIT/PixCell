import gdsfactory as gf

@gf.cell
def create_flower_cross_device():
    c = gf.Component()
    
    # Define cross-section for the petals
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # Create one petal path: start at center, go out, curve back to center
    petal_path = gf.Path()
    petal_path.append(gf.path.straight(length=1.0))        # Go outward
    petal_path.append(gf.path.euler(radius=0.7, angle=90, p=0.5))  # Curve 90°
    petal_path.append(gf.path.euler(radius=0.7, angle=90, p=0.5))  # Curve back
    petal_path.append(gf.path.straight(length=1.0))        # Return to center (optional)
    
    # Extrude to create petal geometry
    petal_component = gf.path.extrude(petal_path, cross_section=xs)
    
    # Create 4 rotated copies of the petal
    north_petal = c << petal_component
    east_petal = c << petal_component
    east_petal.rotate(90)
    south_petal = c << petal_component
    south_petal.rotate(180)
    west_petal = c << petal_component
    west_petal.rotate(270)
    
    # Manually add ports at the tips (no reliance on .ports of petal_component)
    c.add_port("north", center=(0, 2.35), width=0.5, orientation=90, layer=(1, 0))
    c.add_port("east", center=(2.35, 0), width=0.5, orientation=0, layer=(1, 0))
    c.add_port("south", center=(0, -2.35), width=0.5, orientation=270, layer=(1, 0))
    c.add_port("west", center=(-2.35, 0), width=0.5, orientation=180, layer=(1, 0))
    
    return c

# Create the device
device = create_flower_cross_device()

# Optional: Print bounding box to verify footprint
bbox = device.bbox
width = bbox[1][0] - bbox[0][0]
height = bbox[1][1] - bbox[0][1]
print(f"Device footprint: {width:.2f}μm x {height:.2f}μm")

# Save to GDS
device.write_gds("flower_cross_device.gds")