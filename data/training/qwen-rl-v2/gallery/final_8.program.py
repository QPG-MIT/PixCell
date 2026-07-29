import gdsfactory as gf

@gf.cell
def device():
    c = gf.Component()
    
    # Analyze the target image carefully:
    # - Top part: A U-shape or rectangular frame with 5 horizontal white lines cutting through the top portion
    #   The white lines appear as gaps in the black material
    # - Middle: 5 separate horizontal black lines spanning the width
    # - Bottom: A U-shape or rectangular frame with 5 horizontal white lines cutting through the bottom portion
    #   (similar to top but inverted)
    
    # BLACK = material on layer (1,0)
    # WHITE = background (no material)
    
    # The white lines inside the top and bottom blocks mean those regions have NO material on layer (1,0)
    # So I need to construct the black regions, avoiding the white line areas
    
    # Let me define the footprint and structure:
    width_um = 120.0
    height_um = 4.0
    
    # Parameters for the design
    # Top block: solid black frame with 5 horizontal white stripes near the top
    # Middle: 5 horizontal black strips
    # Bottom block: solid black frame with 5 horizontal white stripes near the bottom
    
    # Let me break down vertically (from y=0 at bottom to y=4 at top):
    # Bottom solid region with top portion having 5 white cuts:
    # - Very bottom (y=0 to y~0.3): solid black
    # - Then 5 white horizontal lines with black between them (the white lines are gaps)
    # - Then top solid region up to some y
    
    # Actually, looking again at the image - the "white lines" in top and bottom blocks 
    # are inside the black, meaning black is ON both sides of each white line.
    # So each white line is a narrow unfilled slot within a larger black region.
    
    # Simpler interpretation: 
    # The entire device can be built from horizontal rectangular bars on layer (1,0)
    # The white areas are just empty space between black bars
    
    # Structure (y-coordinates from 0 at bottom to 4 at top):
    # Bottom region: solid black rectangle minus 5 horizontal white slots
    # Middle: 5 separate horizontal black bars
    # Top region: solid black rectangle minus 5 horizontal white slots
    
    # Let me draw it as all black regions (everything is on layer 1,0 if black, nothing if white):
    
    # Bottom rectangular block (from y=0 up to ~1.5, with 5 white horizontal gaps from y~0.5 to y~1.4)
    # This means: 
    # - Solid from y=0 to y=0.5 (black)
    # - White lines at specific y positions with small height
    # - Between white lines: thin black strips
    # - Then solid from y~1.4 to y~1.5 (black)
    
    # Let me simplify by defining parameters:
    num_white_slots = 5
    slot_height = 0.08  # height of each white (unfilled) slot
    slot_gap = 0.06     # black material height between slots
    
    # Middle section height occupied by white slots
    middle_slots_height = num_white_slots * slot_height + (num_white_slots - 1) * slot_gap
    
    # Below the slots block: solid black
    below_slots = 0.5  # height of solid region below all white slots
    
    # Above the slots block in bottom region: small solid region
    above_slots_in_block = 0.3
    
    # Bottom block y-range: 0 to below_slots + middle_slots_height + above_slots_in_block
    bottom_block_upper = below_slots + middle_slots_height + above_slots_in_block
    
    # Now add the solid black rectangle for bottom (excluding white slot areas)
    # I'll add the solid parts and skip the white slot regions
    
    # Part 1: Solid bottom (y=0 to y=0.5)
    bottom_solid = gf.components.rectangle(
        size=(width_um, below_slots),
        layer=(1, 0),
        centered=False
    )
    c << bottom_solid
    
    # Part 2: Thin black strips between/around white slots in bottom block
    # Between each pair of white slots: black strip of height slot_gap
    y_current = below_slots
    for i in range(num_white_slots):
        # Black strip above this white slot (or the initial gap before first slot)
        # White slot at y_current to y_current + slot_height
        # Add black strip after white slot if not the last one
        if i < num_white_slots - 1:
            black_strip_between = y_current + slot_height
            black_strip_bottom = y_current + slot_height
            black_strip_height = slot_gap
            
        # Actually let me redo this more carefully
        
    # Let me think of it as: from y=below_slots to y=above_slots_in_block + below_slots
    # Within this range, there are num_white_slots white slots of height slot_height,
    # separated by black strips of height slot_gap
    
    # White slot positions:
    white_slot_starts = []
    y_pos = below_slots
    for i in range(num_white_slots):
        white_slot_starts.append(y_pos)
        y_pos += slot_height + slot_gap
    
    # Now fill in the black regions:
    # Bottom solid already done (0 to below_slots)
    
    # Between white slots: black strips
    for i in range(num_white_slots - 1):
        # Black strip between slot i and slot i+1
        strip_start = white_slot_starts[i] + slot_height
        strip_height = slot_gap
        strip = gf.components.rectangle(
            size=(width_um, strip_height),
            layer=(1, 0),
            centered=False
        )
        ref = c << strip
        ref.move((0, strip_start))
    
    # Top strip of bottom block (above last white slot)
    top_strip_bottom = white_slot_starts[-1] + slot_height
    top_strip_height = above_slots_in_block
    if top_strip_height > 0:
        top_strip = gf.components.rectangle(
            size=(width_um, top_strip_height),
            layer=(1, 0),
            centered=False
        )
        ref = c << top_strip
        ref.move((0, top_strip_bottom))
    
    # Now middle section: 5 separate black bars (above the white slots of bottom block)
    # Middle bars start after the bottom block gap region
    middle_start_y = white_slot_starts[-1] + slot_height + above_slots_in_block
    middle_bar_height = 0.12
    middle_bar_gap = 0.08
    
    for i in range(5):  # 5 middle bars
        bar_y = middle_start_y + i * (middle_bar_height + middle_bar_gap)
        bar = gf.components.rectangle(
            size=(width_um, middle_bar_height),
            layer=(1, 0),
            centered=False
        )
        ref = c << bar
        ref.move((0, bar_y))
    
    # Now top block: similar to bottom but at top
    # Top block solid region at top + white slots at bottom of top block
    
    # Leftover space after middle bars
    total_middle_bars_height = 5 * middle_bar_height + 4 * middle_bar_gap
    after_middle = middle_start_y + total_middle_bars_height
    
    # Top block: solid region from some y to 4.0, with white slots at its bottom edge
    top_block_solid_top = 3.5  # solid region from y=3.5 to y=4.0
    
    # White slots in top block (lower part of top block)
    top_block_slots_bottom = top_block_solid_top - (num_white_slots * slot_height + (num_white_slots - 1) * slot_gap)
    
    # Black strip below top block's white slots
    if top_block_slots_bottom > 0:
        bottom_strip_height = top_block_slots_bottom - after_middle
        if bottom_strip_height > 0:
            bottom_strip_2 = gf.components.rectangle(
                size=(width_um, bottom_strip_height),
                layer=(1, 0),
                centered=False
            )
            ref = c << bottom_strip_2
            ref.move((0, after_middle))
    
    # White slots in top block - skip these (they're white/background)
    # White slot positions in top block
    top_white_start = top_block_slots_bottom
    for i in range(num_white_slots):
        # White slot from top_white_start + i*(slot_height+slot_gap) to that + slot_height
        pass  # Skip, don't add material here
    
    # Between white slots in top block: black strips
    for i in range(num_white_slots - 1):
        strip_start_2 = top_white_start + i * (slot_height + slot_gap) + slot_height
        strip = gf.components.rectangle(
            size=(width_um, slot_gap),
            layer=(1, 0),
            centered=False
        )
        ref = c << strip
        ref.move((0, strip_start_2))
    
    # Solid top region (already defined to go to y=4.0)
    top_solid = gf.components.rectangle(
        size=(width_um, top_block_solid_top - top_block_slots_bottom),
        layer=(1, 0),
        centered=False
    )
    ref = c << top_solid
    ref.move((0, top_block_slots_bottom))
    
    return c

if __name__ == "__main__":
    dev = device()
    dev.write_gds("device.gds")