import gdsfactory as gf
import numpy as np

@gf.cell
def grating_coupler_device():
    """
    Recreates the grating coupler device with tapered waveguides.
    Footprint: 18.24 x 0.7 um
    """
    c = gf.Component()
    
    # Device dimensions (in micrometers)
    total_length = 18.24
    total_height = 0.7
    
    # Waveguide parameters
    wg_height = 0.22  # Height of each waveguide section
    center_gap = 0.26  # Gap between top and bottom waveguides
    center_line_height = 0.03  # Thin center line
    
    # Taper parameters
    taper_length = 2.0
    taper_tip_width = 0.05
    
    # Grating parameters
    grating_start = 2.5
    grating_end = 15.7
    grating_period = 0.18
    duty_cycle = 0.45
    bar_width = grating_period * duty_cycle
    
    # Create top waveguide with tapers
    # Left taper (top)
    top_left_taper = c << gf.components.taper(
        length=taper_length,
        width1=taper_tip_width,
        width2=wg_height,
        layer=(1, 0)
    )
    top_left_taper.rotate(90)
    top_left_taper.move((0, center_gap/2 + wg_height/2))
    
    # Right taper (top)
    top_right_taper = c << gf.components.taper(
        length=taper_length,
        width1=wg_height,
        width2=taper_tip_width,
        layer=(1, 0)
    )
    top_right_taper.rotate(90)
    top_right_taper.move((total_length - taper_length, center_gap/2 + wg_height/2))
    
    # Bottom waveguide with tapers
    # Left taper (bottom)
    bottom_left_taper = c << gf.components.taper(
        length=taper_length,
        width1=taper_tip_width,
        width2=wg_height,
        layer=(1, 0)
    )
    bottom_left_taper.rotate(90)
    bottom_left_taper.move((0, -center_gap/2 - wg_height/2))
    
    # Right taper (bottom)
    bottom_right_taper = c << gf.components.taper(
        length=taper_length,
        width1=wg_height,
        width2=taper_tip_width,
        layer=(1, 0)
    )
    bottom_right_taper.rotate(90)
    bottom_right_taper.move((total_length - taper_length, -center_gap/2 - wg_height/2))
    
    # Add periodic grating bars
    n_bars = int((grating_end - grating_start) / grating_period)
    
    for i in range(n_bars):
        x_pos = grating_start + i * grating_period
        
        # Top grating bar
        bar_top = c << gf.components.rectangle(
            size=(bar_width, wg_height),
            layer=(1, 0),
            centered=False
        )
        bar_top.move((x_pos, center_gap/2))
        
        # Bottom grating bar
        bar_bottom = c << gf.components.rectangle(
            size=(bar_width, wg_height),
            layer=(1, 0),
            centered=False
        )
        bar_bottom.move((x_pos, -center_gap/2 - wg_height))
    
    # Add center line
    center_line = c << gf.components.rectangle(
        size=(total_length, center_line_height),
        layer=(1, 0),
        centered=False
    )
    center_line.move((0, -center_line_height/2))
    
    return c

# Create the device and save
device = grating_coupler_device()
device.show()  # Optional: display in viewer
device.write_gds("grating_coupler_device.gds")
print("GDS file 'grating_coupler_device.gds' created successfully!")