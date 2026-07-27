import gdsfactory as gf

@gf.cell
def grating_coupler_device():
    """
    Recreation of the device geometry:
    - Central bus: 5 parallel straight waveguides.
    - Top/Bottom blocks: Stack of waveguides that flare outwards at the ends 
      (S-bends) and run straight in the middle.
    - Footprint constraint: 120um x 4um.
    """
    c = gf.Component()

    # --- Dimensions ---
    length_total = 120.0
    height_total = 4.0
    
    # Geometry partition
    # The central straight section looks to cover about 70-80% of the length
    length_flare = 20.0
    length_flat = length_total - 2 * length_flare # 80.0
    
    # Waveguide parameters to achieve the "dense black line" look
    wg_width = 0.15
    wg_gap = 0.05
    pitch = wg_width + wg_gap

    # --- 1. Central Bus ---
    # 5 Straight parallel lines in the center
    # Running the full length of the device (120um)
    num_center_lines = 5
    center_y_start = -((num_center_lines - 1) * pitch) / 2
    
    for i in range(num_center_lines):
        y = center_y_start + i * pitch
        wg = c << gf.components.straight(length=length_total, width=wg_width)
        wg.y = y

    # --- 2. Top Flaring Block ---
    # A stack of waveguides that bend UP at the ends
    # They start above the central bus
    
    num_flare_lines = 5 # Creates the "block" appearance
    # Start gap slightly larger to separate bus from cladding
    start_y_top = center_y_start + (num_center_lines * pitch) + wg_gap 
    
    for i in range(num_flare_lines):
        # Calculate Y position for the straight section
        y_flat = start_y_top + i * pitch
        
        # Calculate Flare Height (dy)
        # The gap opens up at the ends, so dy increases for outer lines.
        # Base flare + incremental flare per layer
        flare_height = 0.2 + (i * 0.15)
        
        # A. Flat Section (Middle)
        flat = c << gf.components.straight(length=length_flat, width=wg_width)
        flat.x = length_total / 2
        flat.y = y_flat
        
        # B. Left S-Bend (Connects to start of flat, flaring OUT/UP to the left)
        # We use bend_s. Standard goes (0,0) -> (L, h).
        # We mirror horizontally to go Left -> Right into the flat section.
        # To connect cleanly: Mirror X, then connect its O1 port to flat O1.
        # This effectively places the bend to the left, starting high and ending at y_flat.
        bend_l = c << gf.components.bend_s(size=(length_flare, flare_height), width=wg_width)
        bend_l.mirror_x() 
        bend_l.connect("o1", flat.ports["o1"])
        
        # C. Right S-Bend (Connects to end of flat, flaring OUT/UP to the right)
        # Standard bend_s goes Right and Up. Perfect.
        bend_r = c << gf.components.bend_s(size=(length_flare, flare_height), width=wg_width)
        bend_r.connect("o1", flat.ports["o2"])

    # --- 3. Bottom Flaring Block ---
    # Mirror of the Top Block (Bending DOWN)
    
    start_y_bot = center_y_start - pitch - wg_gap
    
    for i in range(num_flare_lines):
        # Moving downwards from the center
        y_flat = start_y_bot - i * pitch
        
        # Flare "down" means negative height for bend_s
        flare_height = -(0.2 + (i * 0.15))
        
        # A. Flat Section
        flat = c << gf.components.straight(length=length_flat, width=wg_width)
        flat.x = length_total / 2
        flat.y = y_flat
        
        # B. Left S-Bend (Flaring OUT/DOWN to the left)
        bend_l = c << gf.components.bend_s(size=(length_flare, flare_height), width=wg_width)
        bend_l.mirror_x()
        bend_l.connect("o1", flat.ports["o1"])
        
        # C. Right S-Bend (Flaring OUT/DOWN to the right)
        bend_r = c << gf.components.bend_s(size=(length_flare, flare_height), width=wg_width)
        bend_r.connect("o1", flat.ports["o2"])

    return c

# Create and save the device
device = grating_coupler_device()
device.show() # Views the GDS if KLayout is installed/configured
device.write_gds("recreated_device.gds")