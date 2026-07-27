import gdsfactory as gf

# 1. Define the component using the @gf.cell decorator
@gf.cell
def create_silhouette():
    # We use two components to hold the parts before merging them
    c_body = gf.Component("body")
    c_tapers = gf.Component("tapers")
    
    # Layer definition
    layer = (1, 0)
    
    # 2. Add Main Body (centered)
    body = c_body << gf.components.rectangle(size=(25, 6), layer=layer, centered=True)
    
    # 3. Add Top Tapers
    taper_up = gf.components.taper(length=5, width1=3, width2=1, layer=layer)
    # Positions based on a 25um width
    for x_pos in [-7.5, -2.5, 2.5, 7.5]:
        ref = c_tapers << taper_up
        ref.rotate(90)
        ref.move((x_pos, 3)) # Move to the top edge (3um is half of the 6um body height)
        
    # 4. Add Bottom Taper
    taper_down = gf.components.taper(length=4, width1=4, width2=1, layer=layer)
    ref_bot = c_tapers << taper_down
    ref_bot.rotate(-90)
    ref_bot.move((0, -3)) # Move to the bottom edge
    
    # 5. Boolean Operation
    # Merges the two components into one single polygon silhouette
    c_final = gf.boolean(c_body, c_tapers, operation="or", layer=layer)
    
    return c_final

# Generate the device
device = create_silhouette()

# Save the GDS file
file_path = "silhouette_device.gds"
device.write_gds(file_path)

print(f"Success! GDS file saved to: {file_path}")

# Visualize the file
device.show()