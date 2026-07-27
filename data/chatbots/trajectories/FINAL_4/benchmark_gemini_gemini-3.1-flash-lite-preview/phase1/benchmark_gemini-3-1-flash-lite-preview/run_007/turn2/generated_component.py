import gdsfactory as gf

@gf.cell
def fused_coupler():
    """
    Creates the fused waveguide coupler shape by overlapping two 
    S-bends and using a Boolean OR operation.
    """
    c = gf.Component()
    
    # Define cross-section
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # We use bend_s to create the curvature.
    # We want them to overlap in the middle, so we position one 
    # to curve down and the other to curve up.
    # Total length of 18um matches the footprint constraint.
    s1 = gf.components.bend_s(size=(18, -2.0), cross_section=xs)
    s2 = gf.components.bend_s(size=(18, 2.0), cross_section=xs)
    
    # Add them to the component
    ref1 = c << s1
    ref2 = c << s2
    
    # Offset them vertically so they overlap in the center (forming the waist)
    ref1.movey(1.0)
    ref2.movey(-1.0)
    
    # --- Boolean Operation ---
    # Merge the two references into a single piece of geometry
    combined = gf.boolean(ref1, ref2, operation="or", layer=(1, 0))
    
    # Add the resulting merged geometry to the component
    c << combined
    
    return c

# Generate and save
if __name__ == "__main__":
    device = fused_coupler()
    device.write_gds("fused_coupler.gds")