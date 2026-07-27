import gdsfactory as gf

@gf.cell
def double_waveguide():
    c = gf.Component("double_waveguide")

    # Define waveguide cross-section
    xs = gf.cross_section.cross_section(width=1, layer=(1, 0))

    # Wave parameters
    wave_amplitude = 1  # Amplitude of the sine wave
    wave_period = 6      # Period of the sine wave
    straight_length = 3 # Straight portion length on each side

    # Top waveguide
    path_top = gf.Path()
    path_top.append(gf.path.straight(length=straight_length))
    path_top.append(gf.path.arc(radius=wave_amplitude, angle=180))
    path_top.append(gf.path.straight(length=wave_period - 2 * wave_amplitude))
    path_top.append(gf.path.arc(radius=wave_amplitude, angle=180))
    path_top.append(gf.path.straight(length=straight_length))
    
    top_waveguide = c << gf.path.extrude(path_top, cross_section=xs)
    top_waveguide.move((0,wave_amplitude)) # move above x axis to avoid self intersections with bottom waveguide


    # Bottom waveguide (mirror of top waveguide)
    path_bottom = gf.Path()
    path_bottom.append(gf.path.straight(length=straight_length))
    path_bottom.append(gf.path.arc(radius=wave_amplitude, angle=-180))
    path_bottom.append(gf.path.straight(length=wave_period - 2 * wave_amplitude))
    path_bottom.append(gf.path.arc(radius=wave_amplitude, angle=-180))
    path_bottom.append(gf.path.straight(length=straight_length))

    bottom_waveguide = c << gf.path.extrude(path_bottom, cross_section=xs)
    bottom_waveguide.move((0,-wave_amplitude)) # move below x axis to avoid self intersections with top waveguide

    # Make total width the length of 3 periods
    total_width = 3*wave_period 

    # Move left so it is centered
    c.move((-total_width/2, 0))

    return c


# Create and save the device
device = double_waveguide()
device.write_gds("double_waveguide.gds")

gf.show(device)