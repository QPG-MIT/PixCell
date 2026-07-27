import gdsfactory as gf

@gf.cell
def waveguide_crossing():
    c = gf.Component()
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))

    # Define dimensions based on the 18um x 3um footprint
    # We break the crossing into 4 S-bend primitives
    dx = 9.0
    dy = 1.5

    # --- Construct Top Waveguide ---
    # Segment 1: Start at (0, 1.5), go to (9, 0)
    top_s1 = c << gf.components.bend_s(size=(dx, -dy), cross_section=xs)
    # Segment 2: Start at (9, 0), go to (18, -1.5)
    top_s2 = c << gf.components.bend_s(size=(dx, -dy), cross_section=xs)
    top_s2.connect("o1", top_s1.ports["o2"])

    # --- Construct Bottom Waveguide ---
    # Segment 1: Start at (0, -1.5), go to (9, 0)
    bot_s1 = c << gf.components.bend_s(size=(dx, dy), cross_section=xs)
    # Segment 2: Start at (9, 0), go to (18, 1.5)
    bot_s2 = c << gf.components.bend_s(size=(dx, dy), cross_section=xs)
    bot_s2.connect("o1", bot_s1.ports["o2"])

    # --- Boolean Merge ---
    # Since we have two waveguides that overlap at the center,
    # we flatten them into a single structure using boolean operations.
    
    # Create two components to act as A and B for the boolean operation
    top_wg = gf.Component()
    top_wg << top_s1
    top_wg << top_s2
    
    bot_wg = gf.Component()
    bot_wg << bot_s1
    bot_wg << bot_s2
    
    # Perform the boolean OR to merge them into one continuous X-shape
    crossing = gf.boolean(top_wg, bot_wg, operation="or", layer=(1, 0))
    
    # Add result to main component
    c.add(crossing)

    return c

# Create and save
device = waveguide_crossing()
device.write_gds("waveguide_crossing.gds")