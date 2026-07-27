import gdsfactory as gf
from gdsfactory.component import Component

@gf.cell
def wavy_lines() -> Component:
    """
    Recreates the wavy lines geometry using GDSFactory parametric functions.
    """
    c = gf.Component("wavy_lines")

    # Define the cross-section (width and layer)
    width = 3  # From the footprint the device is 3um tall, 
    # so each line needs to be half that width
    
    xs = gf.cross_section.cross_section(width=width, layer=(1, 0), radius=10) # set min radius
    
    # Define straight waveguide length to have something to attach
    straight_length = 18  # From the footprint, the device is 18um wide
    straight = gf.components.straight(length=straight_length, cross_section=xs)
    
    #Define the bend geometry
    bend_radius = 10 #Estimated from image, at least CrossSection.radius_min
    angle = 45  #Estimated from image
    bend = gf.components.bend_circular(radius=bend_radius, angle=angle, cross_section=xs) #use circular bend for simplicity
    
    # Place the first straight waveguide
    straight1 = c << straight
    
    # Place the first bend and connect it to the first straight
    bend1 = c << bend
    bend1.connect("o1", straight1.ports["o2"])
    
    # mirror bend and attach
    bend2 = c << bend
    bend2.reflect((0,0)) #reflect both X and Y axis to connect.
    bend2.connect("o1", straight1.ports["o1"])
    
    # Place the second straight waveguide and connect
    straight2 = c << straight
    straight2.connect("o2", bend1.ports["o2"])
    
    bend3 = c << bend
    bend3.reflect((1,0)) #reflect X axis to connect.
    bend3.connect("o1", straight2.ports["o1"])
    
    bend4 = c << bend
    bend4.reflect() #reflect both X and Y axis to connect.
    bend4.connect("o2", bend3.ports["o2"])
    
    straight3 = c << straight
    straight3.connect("o1", bend4.ports["o1"])
    
    return c

if __name__ == "__main__":
    c = wavy_lines()
    c.show(show_ports=True)