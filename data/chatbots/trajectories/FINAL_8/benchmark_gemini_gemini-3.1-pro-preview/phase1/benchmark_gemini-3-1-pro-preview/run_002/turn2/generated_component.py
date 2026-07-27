import gdsfactory as gf

@gf.cell
def multi_slot_coupler() -> gf.Component:
    c = gf.Component()

    # To create the "solid block" effect in the middle, the middle y-coordinates (ym) 
    # of the flared groups are spaced exactly by their widths so they touch/merge.
    # The end y-coordinates (ye) are spread out to create the distinct entry ports.
    
    arms = [
        # --- Center Straight Group (4 thin lines, straight through) ---
        {"w": 0.08, "ym": -0.24, "ye": -0.24},
        {"w": 0.08, "ym": -0.08, "ye": -0.08},
        {"w": 0.08, "ym": 0.08, "ye": 0.08},
        {"w": 0.08, "ym": 0.24, "ye": 0.24},

        # --- Top Flared Group (4 thin lines, 1 thick line) ---
        # ym spacing = 0.08 (touches exactly). ye spacing = 0.19 (gap of 0.11)
        {"w": 0.08, "ym": 0.40, "ye": 0.92},
        {"w": 0.08, "ym": 0.48, "ye": 1.11},
        {"w": 0.08, "ym": 0.56, "ye": 1.30},
        {"w": 0.08, "ym": 0.64, "ye": 1.49},
        {"w": 0.36, "ym": 0.86, "ye": 1.82}, # Max Y edge = 1.82 + (0.36/2) = 2.0

        # --- Bottom Flared Group (Mirrored top group) ---
        {"w": 0.08, "ym": -0.40, "ye": -0.92},
        {"w": 0.08, "ym": -0.48, "ye": -1.11},
        {"w": 0.08, "ym": -0.56, "ye": -1.30},
        {"w": 0.08, "ym": -0.64, "ye": -1.49},
        {"w": 0.36, "ym": -0.86, "ye": -1.82}, # Min Y edge = -1.82 - (0.36/2) = -2.0
    ]

    for arm in arms:
        w = arm["w"]
        ym = arm["ym"]
        ye = arm["ye"]
        
        # Define cross-section for the current track
        xs = gf.cross_section.cross_section(width=w, layer=(1, 0))

        if abs(ye - ym) > 1e-6:
            # Outer flared groups: S-bends with different dy will converge/merge
            
            # Left bend transitions from ye to ym
            b_left = c << gf.components.bend_s(size=(40, ym - ye), cross_section=xs)
            b_left.move((0, ye))

            # Middle horizontal section (these will touch and form a solid block)
            s_mid = c << gf.components.straight(length=40, cross_section=xs)
            s_mid.connect("o1", b_left.ports["o2"])

            # Right bend transitions back from ym to ye
            b_right = c << gf.components.bend_s(size=(40, ye - ym), cross_section=xs)
            b_right.connect("o1", s_mid.ports["o2"])
        else:
            # Central group: Continuous straight lines
            s = c << gf.components.straight(length=120, cross_section=xs)
            s.move((0, ym))

    return c

if __name__ == "__main__":
    # Generate the device
    device = multi_slot_coupler()
    
    # Save the geometry to a GDS file
    device.write_gds("multi_slot_coupler.gds")