import gdsfactory as gf

@gf.cell
def edge_coupler_structure() -> gf.Component:
    """
    Recreates the device geometry shown in the image using core parametric primitives.
    Target footprint: exactly [40.0, 1.7] (Length x Width)
    """
    c = gf.Component("edge_coupler_structure")
    layer = (1, 0)
    
    # ---------------------------------------------------------
    # 1. Center Waveguide
    # ---------------------------------------------------------
    # Initial straight segment (Starts at X=0, length=4.0)
    xs_center = gf.cross_section.cross_section(width=0.30, layer=layer)
    center_str = c << gf.components.straight(length=4.0, cross_section=xs_center)
    
    # Tapering down to a sharp point (Length=20.0, ends at X=24.0)
    center_tap = c << gf.components.taper(
        length=20.0, 
        width1=0.30, 
        width2=0.02, 
        layer=layer
    )
    center_tap.connect("o1", center_str.ports["o2"])

    # ---------------------------------------------------------
    # 2. Left Outer Arms (Flat outer boundaries, tapered inner gap)
    # ---------------------------------------------------------
    # We create the perfectly flat outer edge and smoothly narrowing inner gap using a Boolean subtraction.
    
    # Bounding box width = 0.90 (Outer bounds at Y = -0.45 to +0.45)
    xs_bbox = gf.cross_section.cross_section(width=0.90, layer=layer)
    bbox = gf.components.straight(length=20.0, cross_section=xs_bbox)
    
    # Central hole to subtract (Tapers from width 0.82 to 0.30)
    # This leaves outer arms that go from 0.04 width at X=4, to 0.30 width at X=24.
    hole = gf.components.taper(length=20.0, width1=0.82, width2=0.30, layer=layer)
    
    # Perform subtraction and place starting at the end of the center straight (X=4.0)
    arms_left = gf.boolean(bbox, hole, operation="not", layer=layer)
    ref_arms_left = c << arms_left
    ref_arms_left.movex(4.0)

    # ---------------------------------------------------------
    # 3. Right S-Bends
    # ---------------------------------------------------------
    # Connecting to the ends of the left outer arms at X=24.0
    xs_arms = gf.cross_section.cross_section(width=0.30, layer=layer)
    
    # Top S-Bend: Moves from Y=0.30 (center of top left arm) to Y=0.70 (dy = +0.40)
    sbend_top = c << gf.components.bend_s(size=(10.0, 0.40), cross_section=xs_arms)
    sbend_top.move((24.0, 0.30)) 
    
    # Bottom S-Bend: Moves from Y=-0.30 (center of bottom left arm) to Y=-0.70 (dy = -0.40)
    sbend_bot = c << gf.components.bend_s(size=(10.0, -0.40), cross_section=xs_arms)
    sbend_bot.move((24.0, -0.30))

    # ---------------------------------------------------------
    # 4. Final Straights
    # ---------------------------------------------------------
    # Completes the layout to reach exactly Length = 40.0
    str_final = gf.components.straight(length=6.0, cross_section=xs_arms)
    
    ref_str_top = c << str_final
    ref_str_top.connect("o1", sbend_top.ports["o2"])
    # The top edge of this arm will sit at Y = 0.70 + (0.30/2) = 0.85
    
    ref_str_bot = c << str_final
    ref_str_bot.connect("o1", sbend_bot.ports["o2"])
    # The bottom edge of this arm will sit at Y = -0.70 - (0.30/2) = -0.85
    
    # Total Final Footprint Verification:
    # Length: 4 (str) + 20 (left taper) + 10 (S-bend) + 6 (final str) = 40.0
    # Width: Max +Y is 0.85, Min -Y is -0.85 -> 0.85 - (-0.85) = 1.70
    
    return c

if __name__ == "__main__":
    # Generate the component
    c = edge_coupler_structure()
    
    # Explicitly write the GDS file required by the evaluation environment
    c.write_gds("edge_coupler_structure.gds")