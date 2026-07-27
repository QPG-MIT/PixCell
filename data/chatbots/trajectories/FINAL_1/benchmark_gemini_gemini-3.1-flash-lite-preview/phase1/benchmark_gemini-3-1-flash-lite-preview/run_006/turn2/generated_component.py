import gdsfactory as gf

@gf.cell
def y_splitter_device():
    # 1. Define the cross-sections for the taper transition
    # Start width 0.3, End width 0.8
    xs_start = gf.cross_section.cross_section(width=0.3, layer=(1, 0))
    xs_end = gf.cross_section.cross_section(width=0.8, layer=(1, 0))
    
    # 2. Create the transition object for the extrusion
    transition = gf.path.transition(xs_start, xs_end)
    
    # 3. Create paths for the two arms
    # Path 1: Straight, then angled up
    p1 = gf.Path()
    p1.append(gf.path.straight(length=40))
    p1.rotate(angle=2.5) # Slight angle
    
    # Path 2: Straight, then angled down
    p2 = gf.Path()
    p2.append(gf.path.straight(length=40))
    p2.rotate(angle=-2.5) # Inverse angle
    
    # 4. Create the component
    c = gf.Component("y_splitter")
    
    # 5. Extrude the paths into 3D geometry
    # This automatically merges them at the origin (0,0)
    arm1 = c << gf.path.extrude_transition(p1, transition)
    arm2 = c << gf.path.extrude_transition(p2, transition)
    
    return c

if __name__ == "__main__":
    device = y_splitter_device()
    device.write_gds("y_splitter.gds")
    device.show()
    print("GDS file 'y_splitter.gds' has been generated.")