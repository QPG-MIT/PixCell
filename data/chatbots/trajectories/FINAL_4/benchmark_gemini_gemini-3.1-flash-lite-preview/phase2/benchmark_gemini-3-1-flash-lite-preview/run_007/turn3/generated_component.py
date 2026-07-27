import gdsfactory as gf

@gf.cell
def fused_coupler():
    """
    Creates a fused waveguide coupler shape by mirroring two 
    S-bends and using a Boolean OR operation.
    """
    c = gf.Component()
    
    # Define cross-section
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # We use bend_s to create the curvature.
    # By using the same bend_s and mirroring one, they will be 
    # symmetric and will meet in the middle rather than crossing.
    s1 = gf.components.bend_s(size=(18, 1.0), cross_section=xs)
    s2 = gf.components.bend_s(size=(18, 1.0), cross_section=xs)
    
    # Add them to a temporary component to manage positions before boolean
    tmp = gf.Component()
    r1 = tmp << s1
    r2 = tmp << s2
    
    # Mirror and offset to make them symmetric and touch in the middle
    r2.mirror()
    
    # Move them so they are centered vertically and touch in the center
    # r1 starts at y=0, r2 starts at y=0 (mirrored), move them apart
    r1.movey(0.5)
    r2.movey(-0.5)
    
    # --- Boolean Operation ---
    # Merge the two references into a single piece of geometry
    merged = gf.boolean(r1, r2, operation="or", layer=(1, 0))
    
    # Add the resulting merged geometry to the main component
    c << merged
    
    return c

# Generate and save
if __name__ == "__main__":
    device = fused_coupler()
    device.write_gds("fused_coupler.gds")