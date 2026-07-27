import gdsfactory as gf
import functools

# ==============================================================================
# 1. Define Custom Cross-Sections
# ==============================================================================

# Custom XS for the tight bends (allows R=1.25um)
xs_tight = gf.cross_section.cross_section(
    width=0.5,
    layer=(1, 0),
    radius=1.25,
    radius_min=0.5
)

# Custom XS for the straight sections (defines layer and width)
# We use partial to create a 'factory' or just an object we can reuse
xs_straight_def = gf.cross_section.cross_section(
    width=0.5, 
    layer=(1, 0)
)

# ==============================================================================
# 2. Define Sub-Components
# ==============================================================================

@gf.cell
def perforated_pad(length=0.7, width=1.0, hole_size=(0.4, 0.4), layer=(1, 0)):
    """
    Rectangular pad with a central hole.
    Uses basic shapes (rectangle), which accept 'layer' directly.
    """
    c = gf.Component()
    
    # Create the solid block
    rect = gf.components.rectangle(size=(length, width), centered=True, layer=layer)
    
    # Create the hole
    hole = gf.components.rectangle(size=hole_size, centered=True, layer=layer)
    
    # Create the perforated geometry
    p = c << gf.boolean(rect, hole, operation="not", layer=layer)
    
    # Manually add ports (boolean destroys them)
    c.add_port("o1", center=(-length/2, 0), width=width, orientation=180, layer=layer)
    c.add_port("o2", center=(length/2, 0), width=width, orientation=0, layer=layer)
    return c

@gf.cell
def segmented_arm(layer=(1, 0)):
    """
    The straight arm: Taper -> Pad -> Bridge -> Pad -> Taper
    Total Length target to match footprint: 3.0um (5.5 - 1.25*2)
    """
    c = gf.Component()
    
    # Dimensions
    w_wg = 0.5
    w_pad = 1.0
    
    # Lengths adjusted to sum to 3.0um
    l_taper = 0.4
    l_pad = 0.7
    # Sum so far: 0.4 + 0.7 + 0.7 + 0.4 = 2.2
    # Required Bridge length: 3.0 - 2.2 = 0.8
    l_bridge = 0.8
    
    # Define a cross_section for this specific layer/width combination
    # This prevents the "unexpected keyword argument 'layer'" error
    xs_ref = gf.cross_section.cross_section(width=w_wg, layer=layer)

    # 1. Input Taper
    # Note: taper uses cross_section for layer definition, but width1/width2 override the width
    taper_in = c << gf.components.taper(
        length=l_taper, 
        width1=w_wg, 
        width2=w_pad, 
        cross_section=xs_ref
    )

    # 2. Pad 1
    pad1 = c << perforated_pad(length=l_pad, width=w_pad, layer=layer)

    # 3. Bridge (Straight waveguide)
    # FIX: Use 'cross_section' instead of passing width/layer directly
    bridge = c << gf.components.straight(
        length=l_bridge, 
        cross_section=xs_ref
    )

    # 4. Pad 2
    pad2 = c << perforated_pad(length=l_pad, width=w_pad, layer=layer)

    # 5. Output Taper
    taper_out = c << gf.components.taper(
        length=l_taper, 
        width1=w_pad, 
        width2=w_wg, 
        cross_section=xs_ref
    )
    
    # Connect the chain
    pad1.connect("o1", taper_in.ports["o2"])
    bridge.connect("o1", pad1.ports["o2"])
    pad2.connect("o1", bridge.ports["o2"])
    taper_out.connect("o1", pad2.ports["o2"])
    
    # Expose ports
    c.add_port("o1", port=taper_in.ports["o1"])
    c.add_port("o2", port=taper_out.ports["o2"])
    
    return c

# ==============================================================================
# 3. Final Assembly
# ==============================================================================

@gf.cell
def custom_racetrack_device():
    c = gf.Component()
    
    # Parameters
    radius = 1.25
    
    # Create bends with custom tight cross-section
    bend_left = c << gf.components.bend_euler(
        angle=180, 
        radius=radius, 
        cross_section=xs_tight
    )
    
    bend_right = c << gf.components.bend_euler(
        angle=180, 
        radius=radius, 
        cross_section=xs_tight
    )
    
    # Create arms
    top_arm = c << segmented_arm(layer=(1, 0))
    bot_arm = c << segmented_arm(layer=(1, 0))
    
    # Assemble
    # 1. Top Arm to Left Bend (Top-Left)
    # bend_left port "o2" is the top port
    top_arm.connect("o1", bend_left.ports["o2"])
    
    # 2. Right Bend to Top Arm (Top-Right)
    bend_right.connect("o1", top_arm.ports["o2"])
    
    # 3. Bottom Arm to Right Bend (Bottom-Right)
    bot_arm.connect("o2", bend_right.ports["o2"])
    
    # 4. Close loop (Bottom-Left)
    bend_left.connect("o1", bot_arm.ports["o1"])

    return c

# ==============================================================================
# 4. Execution
# ==============================================================================

if __name__ == "__main__":
    device = custom_racetrack_device()
    
    # Verify Footprint
    bbox = device.bbox
    dx = bbox[1][0] - bbox[0][0]
    dy = bbox[1][1] - bbox[0][1]
    print(f"Final Footprint: {dx:.2f} um x {dy:.2f} um") # Should be ~5.5 x 3.0
    
    device.show()
    device.write_gds("custom_racetrack_fixed.gds")