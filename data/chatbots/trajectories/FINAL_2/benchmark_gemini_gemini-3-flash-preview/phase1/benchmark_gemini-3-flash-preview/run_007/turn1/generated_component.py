import gdsfactory as gf

@gf.cell
def recreate_device_silhouette():
    """
    Recreates the device silhouette using GDSFactory parametric primitives.
    Footprint constraint: 25um (width) x 10um (height)
    """
    layer = (1, 0)
    
    # 1. Create the central body
    # Positioned from y=-2 to y=2 (Height = 4)
    body = gf.components.rectangle(size=(18, 4), layer=layer, centered=True)
    
    # 2. Define the Top Pillar (composed of taper + straight tip)
    # Taper is 3um long; straight tip is 1um long. Total 4um.
    tp_taper = gf.components.taper(length=3.0, width1=1.8, width2=1.0, layer=layer)
    tp_tip = gf.components.rectangle(size=(1.0, 1.0), layer=layer, centered=True)
    
    tp = gf.Component("top_pillar_sub")
    tp << tp_taper
    # Move tip to the end of the taper (which is at x=3.0)
    tp_tip_ref = tp << tp_tip
    tp_tip_ref.movex(3.0 + 0.5) 
    
    # 3. Define the Bottom Pillar
    # Taper is 1.5um long; straight tip is 0.5um long. Total 2um.
    bp_taper = gf.components.taper(length=1.5, width1=2.0, width2=1.2, layer=layer)
    bp_tip = gf.components.rectangle(size=(0.5, 1.2), layer=layer, centered=True)
    
    bp = gf.Component("bottom_pillar_sub")
    bp << bp_taper
    bp_tip_ref = bp << bp_tip
    bp_tip_ref.movex(1.5 + 0.25)

    # 4. Assemble and Merge using Boolean Operations
    # We start with the body and 'OR' each pillar into it to create one silhouette
    combined = body
    
    # Add 4 Top Pillars at y=2.0 (top edge of body)
    top_x_positions = [-6.5, -2.2, 2.2, 6.5]
    for x in top_x_positions:
        temp_comp = gf.Component()
        ref = temp_comp << tp
        ref.rotate(90)
        ref.move((x, 2.0))
        combined = gf.boolean(A=combined, B=temp_comp, operation="or", layer=layer)
        
    # Add 1 Bottom Pillar at y=-2.0 (bottom edge of body)
    temp_bot = gf.Component()
    ref_b = temp_bot << bp
    ref_b.rotate(-90)
    ref_b.move((0, -2.0))
    
    final_component = gf.boolean(A=combined, B=temp_bot, operation="or", layer=layer)
    final_component.name = "device_silhouette"
    
    return final_component

if __name__ == "__main__":
    # Generate component
    c = recreate_device_silhouette()
    
    # Save to GDS file
    filename = "device_reconstruction.gds"
    c.write_gds(filename)
    
    print(f"Successfully generated GDS file: {filename}")