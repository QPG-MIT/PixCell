import gdsfactory as gf

@gf.cell
def recreated_device():
    """
    Recreation of the slotted directional coupler device.
    Refined for higher fill factor, 4-line wings, and tighter spacing
    to match the reference image.
    """
    c = gf.Component()
    
    # =======================================================================
    # 1. Define High-Density Parametric Cross-Sections
    # =======================================================================
    # Tuned for "Bold" look: Thicker lines, thinner gaps.
    # Grid estimation: Pitch = 0.2um (Width 0.14, Gap 0.06)
    
    wg_width = 0.14
    wg_gap = 0.06
    pitch = wg_width + wg_gap
    
    # --- Central Bus (5 lines) ---
    # Centered on y=0
    # Offsets: 0, +/- 0.2, +/- 0.4
    sections_center = [
        gf.cross_section.Section(width=wg_width, offset=0, layer=(1, 0)),
        gf.cross_section.Section(width=wg_width, offset=pitch, layer=(1, 0)),
        gf.cross_section.Section(width=wg_width, offset=2*pitch, layer=(1, 0)),
        gf.cross_section.Section(width=wg_width, offset=-pitch, layer=(1, 0)),
        gf.cross_section.Section(width=wg_width, offset=-2*pitch, layer=(1, 0)),
    ]
    xs_center = gf.cross_section.cross_section(
        width=wg_width, # core width (unused by sections, but required)
        layer=(1, 0), 
        sections=sections_center
    )
    # Calculate geometric top edge of central bus for positioning
    # Top line center at 0.4. Edge at 0.4 + 0.14/2 = 0.47
    center_top_edge = 2*pitch + wg_width/2

    # --- Wing Cross-Section (4 lines) ---
    # We define the path as the "center of the bundle" to ensure symmetric bending.
    # 4 lines -> Offsets: -1.5p, -0.5p, 0.5p, 1.5p
    # Offsets: -0.3, -0.1, 0.1, 0.3
    sections_wing = [
        gf.cross_section.Section(width=wg_width, offset=1.5*pitch, layer=(1, 0)),
        gf.cross_section.Section(width=wg_width, offset=0.5*pitch, layer=(1, 0)),
        gf.cross_section.Section(width=wg_width, offset=-0.5*pitch, layer=(1, 0)),
        gf.cross_section.Section(width=wg_width, offset=-1.5*pitch, layer=(1, 0)),
    ]
    xs_wing = gf.cross_section.cross_section(
        width=wg_width, 
        layer=(1, 0), 
        sections=sections_wing
    )
    # Calculate geometric bottom edge of wing bundle relative to its path center
    # Bottom line center at -0.3. Edge at -0.3 - 0.07 = -0.37
    wing_bundle_bottom_offset = -1.5*pitch - wg_width/2

    # =======================================================================
    # 2. Build Geometry
    # =======================================================================

    # 2.1 Central Bus
    central_wg = c << gf.components.straight(length=120, cross_section=xs_center)
    central_wg.center = (60, 0)

    # 2.2 Calculate Vertical Positions
    # Desired gap at waist (closest point)
    gap_at_waist = 0.08  # Very tight, as seen in image
    
    # Y position of the wing's lowest metal edge
    waist_metal_y = center_top_edge + gap_at_waist
    
    # Y position of the wing's PATH center at the waist
    # path_y + bottom_offset = waist_metal_y  =>  path_y = waist_metal_y - bottom_offset
    waist_path_y = waist_metal_y - wing_bundle_bottom_offset

    # S-Bend Parameters
    # Total footprint height budget is 4um. Center is ~1um. Wings ~0.8um each.
    # Leaving ~1.4um for spacing. 
    # Let's set the input/output Y high enough to create the distinct curve.
    bend_height = 0.65  # Vertical travel of the S-bend
    
    # 2.3 Define S-Bends
    # Bend Down: Starts high, ends low (at waist)
    bend_down = gf.components.bend_s(
        size=(60, -bend_height), 
        cross_section=xs_wing
    )
    # Bend Up: Starts low (at waist), ends high
    bend_up = gf.components.bend_s(
        size=(60, bend_height), 
        cross_section=xs_wing
    )

    # --- Top Wing Assembly ---
    tl = c << bend_down
    tr = c << bend_up
    
    tr.connect("o1", tl.ports["o2"])
    
    # Position the assembly
    # The junction (tl.o2) is the lowest point of the path. Align this to waist_path_y.
    current_junction_y = tl.ports["o2"].y
    move_y = waist_path_y - current_junction_y
    tl.movey(move_y)
    tr.movey(move_y)
    
    # Align X
    tl.xmin = 0

    # --- Bottom Wing Assembly ---
    bl = c << bend_down
    br = c << bend_up
    
    bl.mirror_y()
    br.mirror_y()
    
    br.connect("o1", bl.ports["o2"])
    
    # Mirror positioning implies waist is at -waist_path_y
    current_bot_junction_y = bl.ports["o2"].y
    move_bot_y = (-waist_path_y) - current_bot_junction_y
    bl.movey(move_bot_y)
    br.movey(move_bot_y)
    
    bl.xmin = 0

    return c

# =======================================================================
# 3. Output
# =======================================================================
if __name__ == "__main__":
    device = recreated_device()
    device.show()
    device.write_gds("slotted_coupler_refined.gds")
    
    # Dimensions check
    w = device.dxmax - device.dxmin
    h = device.dymax - device.dymin
    print(f"Device Size: ({w:.2f}, {h:.2f})")