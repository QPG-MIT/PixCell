import gdsfactory as gf

@gf.cell
def fused_coupler():
    """
    Creates a fused waveguide coupler by boolean merging two S-bends.
    We manipulate the components directly to avoid reference-related errors.
    """
    c = gf.Component()
    
    # Define cross-section
    # Increase width slightly to ensure fusion overlap
    xs = gf.cross_section.cross_section(width=0.8, layer=(1, 0))
    
    # 1. Create the base component
    # bend_s creates an S-shape.
    # size=(18, 1.0) means length 18, offset 1.0
    c1 = gf.components.bend_s(size=(18, 1.0), cross_section=xs)
    
    # 2. Create the second component by mirroring the first
    # Using .copy() ensures we have a separate component definition to mirror
    c2 = c1.copy()
    c2.mirror(p1=(0, 0), p2=(1, 0))
    
    # 3. Align them for fusion
    # We move the mirrored one so the middle of the S-bends overlap.
    # c1 goes from y=0 to y=1.0. 
    # c2 (mirrored) effectively starts at y=0. We move it down.
    c2.movey(-1.0)
    
    # --- Boolean Operation ---
    # We pass the components c1 and c2 directly (not references)
    # This avoids the TKCell/Instance AttributeError.
    merged = gf.boolean(c1, c2, operation="or", layer=(1, 0))
    
    # Add the merged geometry to the main component
    c << merged
    
    return c

# Generate and save
if __name__ == "__main__":
    device = fused_coupler()
    device.write_gds("fused_coupler.gds")