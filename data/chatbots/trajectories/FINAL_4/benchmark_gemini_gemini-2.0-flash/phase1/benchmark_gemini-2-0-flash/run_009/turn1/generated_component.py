import gdsfactory as gf
from gdsfactory.component import Component
from gdsfactory.port import Port

@gf.cell
def waved_structure(width: float = 3, period: float = 9, amplitude: float = 1, n_periods: int = 2) -> Component:
    """
    Creates a waved structure using parametric primitives.

    Args:
        width: Width of the waveguide.
        period: Period of the wave.
        amplitude: Amplitude of the wave.
        n_periods: Number of periods.

    """
    c = gf.Component("waved_structure")

    # Create the path for the top waveguide
    p_top = gf.Path()
    p_top.append(gf.path.arc(radius=amplitude, angle=180))
    for i in range(n_periods-1):
        p_top.append(gf.path.arc(radius=-amplitude, angle=180))
        p_top.append(gf.path.arc(radius=amplitude, angle=180))

    # Create the path for the bottom waveguide
    p_bottom = gf.Path()
    p_bottom.append(gf.path.arc(radius=-amplitude, angle=180))
    for i in range(n_periods-1):
        p_bottom.append(gf.path.arc(radius=amplitude, angle=180))
        p_bottom.append(gf.path.arc(radius=-amplitude, angle=180))


    # Extrude the paths to create waveguides
    xs = gf.cross_section.strip(width=width)
    top_waveguide = p_top.extrude(cross_section=xs)
    bottom_waveguide = p_bottom.extrude(cross_section=xs)

    # Add the top waveguide to the component
    top_ref = c << top_waveguide
    top_ref.movey(amplitude+width)

    # Add the bottom waveguide to the component
    bottom_ref = c << bottom_waveguide

    
    c.add_port("o1", port=top_ref.ports["o1"])
    c.add_port("o2", port=top_ref.ports["o2"])
    c.add_port("o3", port=bottom_ref.ports["o1"])
    c.add_port("o4", port=bottom_ref.ports["o2"])
    
    #Add constraints
    #c.add_ports() # Remove this line as it causes error, ports are already added above

    footprint_x = n_periods * period
    footprint_y = 2 * (amplitude+width)
    c.info['footprint_um'] = [footprint_x, footprint_y] # this doesnt work - investigate
    
    return c

if __name__ == "__main__":
    c = waved_structure()
    c.show(show_ports=True)