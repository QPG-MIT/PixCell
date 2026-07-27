import gdsfactory as gf

@gf.cell
def directional_coupler_fixed():
    """
    Directional coupler with 4um x 240um footprint.
    Consists of a central straight coupling region and S-bend inputs/outputs.
    """
    c = gf.Component("Directional_Coupler_4x240")

    # =============================================================
    # 1. Define Parameters & Constraints
    # =============================================================
    # Footprint constraints
    total_length = 240.0
    total_height = 4.0
    
    # Waveguide specs
    wg_width = 0.5
    coupling_gap = 0.2
    
    # Longitudinal Dimensions
    # We estimate the coupling region (straight part) to be 40um.
    # The remaining length is split equally for the input/output S-bends.
    len_coupling = 40.0
    len_bend = (total_length - len_coupling) / 2  # (240 - 40)/2 = 100.0 um

    # Vertical Dimensions (Y-axis geometry)
    # 1. Outer Ports: Centered within the 4um bounding box.
    #    Max top Y = 2.0. Center of WG = 2.0 - (width/2) = 1.75
    y_port_offset = (total_height / 2) - (wg_width / 2) # +/- 1.75 um
    
    # 2. Inner Coupling: Separated by 0.2um gap.
    #    Center of WG = (gap/2) + (width/2) = 0.1 + 0.25 = 0.35
    y_couple_offset = (coupling_gap / 2) + (wg_width / 2) # +/- 0.35 um
    
    # 3. S-Bend Height (dy): Difference between outer port and inner coupler
    dy = y_port_offset - y_couple_offset # 1.75 - 0.35 = 1.4 um

    # Define Cross Section
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))

    # =============================================================
    # 2. Create Primitives
    # =============================================================
    
    # Center: Straight Coupler
    coupler_core = c << gf.components.coupler_straight(
        length=len_coupling,
        gap=coupling_gap,
        cross_section=xs
    )

    # Input/Output: S-Bends
    # We define a bend that moves +X by len_bend and +Y by dy.
    # We will mirror this component as needed for the different corners.
    bend_ref = gf.components.bend_s(
        size=(len_bend, dy), 
        cross_section=xs
    )

    # =============================================================
    # 3. Assembly & Routing
    # =============================================================

    # --- Input Side (Left) ---
    
    # Top-Left Input: Needs to go from Port (High Y) -> Coupler (Low Y)
    # We take the base bend (which goes Low->High) and mirror vertically.
    in_top = c << bend_ref
    in_top.mirror_y()
    # Connect the "end" of the bend (o2) to the start of the coupler (o2 - top west)
    in_top.connect("o2", coupler_core.ports["o2"])

    # Bottom-Left Input: Needs to go from Port (Low Y) -> Coupler (High Y relative to port)
    # The base bend goes Low->High, so we use it directly.
    in_bot = c << bend_ref
    in_bot.connect("o2", coupler_core.ports["o1"])

    # --- Output Side (Right) ---

    # Top-Right Output: From Coupler (Low Y) -> Port (High Y)
    # Base bend goes Low->High.
    out_top = c << bend_ref
    out_top.connect("o1", coupler_core.ports["o3"])

    # Bottom-Right Output: From Coupler (High Y) -> Port (Low Y)
    # Mirror vertically.
    out_bot = c << bend_ref
    out_bot.mirror_y()
    out_bot.connect("o1", coupler_core.ports["o4"])

    # =============================================================
    # 4. Finalize
    # =============================================================
    # Expose ports for external connectivity
    c.add_port("o1", port=in_bot.ports["o1"])
    c.add_port("o2", port=in_top.ports["o1"])
    c.add_port("o3", port=out_top.ports["o2"])
    c.add_port("o4", port=out_bot.ports["o2"])

    return c

if __name__ == "__main__":
    # Generate the component
    device = directional_coupler_fixed()
    
    # Print verification stats
    print(f"Device Name: {device.name}")
    print(f"BBox: {device.bbox}")  # Expected: (0, -2.0) to (240, 2.0)
    
    # Save GDS file
    gds_filename = "directional_coupler_4x240.gds"
    device.write_gds(gds_filename)
    print(f"Success! GDS file saved to: {gds_filename}")