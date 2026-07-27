import gdsfactory as gf

@gf.cell
def recreated_device_geometry():
    """
    Recreates the multi-line waveguide structure from the image.
    Footprint: [120, 4]
    """
    c = gf.Component("recreated_device")
    
    # --- Parameters ---
    total_width = 120.0
    assembly_width = 100.0
    
    # Central Bus Parameters (5 lines)
    num_bus_lines = 5
    bus_line_width = 0.12
    bus_line_pitch = 0.25
    
    # Superstructure Parameters (Thick block + 4 thin lines)
    thick_block_height = 0.6
    thick_block_y_offset = 0.7  # Vertical distance from center to bottom of block
    
    thin_line_count = 4
    thin_line_width = 0.08
    thin_line_pitch = 0.18
    thin_line_gap = 0.12  # Gap between thick block and first thin line
    
    vertical_bar_width = 1.2
    vertical_bar_height = 1.5  # Covers block and lines with "ears"
    
    # --- 1. Central Bus Construction ---
    for i in range(num_bus_lines):
        y_pos = (i - (num_bus_lines - 1) / 2) * bus_line_pitch
        # Using gf.components.straight for horizontal lines
        line = c << gf.components.straight(length=total_width, width=bus_line_width)
        line.movey(y_pos)

    # --- 2. Superstructure (Top/Bottom) Construction ---
    def make_superstructure():
        s = gf.Component()
        
        # Thick horizontal block
        thick_rect = gf.components.rectangle(
            size=(assembly_width, thick_block_height), 
            layer=(1, 0), 
            centered=True
        )
        thick_ref = s << thick_rect
        thick_ref.movey(thick_block_y_offset + thick_block_height / 2)
        
        # 4 thin horizontal lines above the block
        start_y = thick_block_y_offset + thick_block_height + thin_line_gap
        for i in range(thin_line_count):
            y = start_y + (i * thin_line_pitch)
            line = s << gf.components.straight(length=assembly_width, width=thin_line_width)
            line.movey(y)
            
        # Vertical end bars (the "ears")
        # These connect the thick block and thin lines at both ends
        v_bar_rect = gf.components.rectangle(
            size=(vertical_bar_width, vertical_bar_height), 
            layer=(1, 0), 
            centered=True
        )
        
        # Position vertical bars at +/- ends of the assembly
        for x_sign in [-1, 1]:
            bar = s << v_bar_rect
            bar.movex(x_sign * assembly_width / 2)
            # Center the bar vertically across the horizontal stack
            bar_y_center = (thick_block_y_offset + (start_y + (thin_line_count-1)*thin_line_pitch)) / 2
            bar.movey(bar_y_center)
            
        return s

    # Add Top Superstructure
    top = c << make_superstructure()
    
    # Add Bottom Superstructure (Mirrored)
    bottom = c << make_superstructure()
    bottom.mirror_y()
    
    return c

if __name__ == "__main__":
    # Create the component
    component = recreated_device_geometry()
    
    # Save as GDS
    component.write_gds("recreated_device.gds")
    
    # Visualize
    component.show()