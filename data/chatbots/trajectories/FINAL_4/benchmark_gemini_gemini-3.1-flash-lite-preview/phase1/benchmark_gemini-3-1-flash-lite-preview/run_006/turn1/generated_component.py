import gdsfactory as gf

# 1. Define a custom cross-section with a small radius.
# This prevents the "min_bend_radius" error by allowing tight bends.
xs = gf.cross_section.cross_section(
    width=0.5, 
    layer=(1, 0), 
    radius=1.0
)

@gf.cell
def coupled_waveguides():
    """
    Creates the coupled waveguide geometry using parametric primitives.
    Total Footprint constrained to 18um length.
    """
    c = gf.Component()
    
    # Define lengths to fit in 18um
    # (4um straight) + (4um S-bend) + (2um center) + (4um S-bend) + (4um straight) = 18um
    straight_len = 4
    sbend_len = 4
    center_len = 2
    
    # Define shift for S-bend (half the distance required to bring waveguides together)
    # Start gap ~1.5um, End gap ~0.7um. Shift required = 0.4um.
    shift = 0.4
    
    # --- Top Arm ---
    # Start
    top_in = c << gf.components.straight(length=straight_len, cross_section=xs)
    
    # Inward S-bend
    top_bend1 = c << gf.components.bend_s(size=(sbend_len, -shift), cross_section=xs)
    top_bend1.connect("o1", top_in.ports["o2"])
    
    # Center
    top_center = c << gf.components.straight(length=center_len, cross_section=xs)
    top_center.connect("o1", top_bend1.ports["o2"])
    
    # Outward S-bend
    top_bend2 = c << gf.components.bend_s(size=(sbend_len, shift), cross_section=xs)
    top_bend2.connect("o1", top_center.ports["o2"])
    
    # End
    top_out = c << gf.components.straight(length=straight_len, cross_section=xs)
    top_out.connect("o1", top_bend2.ports["o2"])

    # --- Bottom Arm (Mirror) ---
    # Start at Y = -1.5 (to create the initial gap)
    bot_in = c << gf.components.straight(length=straight_len, cross_section=xs)
    bot_in.movey(-1.5)
    
    # Outward S-bend
    bot_bend1 = c << gf.components.bend_s(size=(sbend_len, shift), cross_section=xs)
    bot_bend1.connect("o1", bot_in.ports["o2"])
    
    # Center
    bot_center = c << gf.components.straight(length=center_len, cross_section=xs)
    bot_center.connect("o1", bot_bend1.ports["o2"])
    
    # Inward S-bend
    bot_bend2 = c << gf.components.bend_s(size=(sbend_len, -shift), cross_section=xs)
    bot_bend2.connect("o1", bot_center.ports["o2"])
    
    # End
    bot_out = c << gf.components.straight(length=straight_len, cross_section=xs)
    bot_out.connect("o1", bot_bend2.ports["o2"])

    return c

if __name__ == "__main__":
    # Generate the component
    device = coupled_waveguides()
    
    # Explicitly write the GDS file to the working directory
    device.write_gds("coupled_waveguides.gds")
    
    # Optional: Open in viewer (if GDSFactory/KLayout is installed)
    print("GDS file generated: coupled_waveguides.gds")