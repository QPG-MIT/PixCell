import gdsfactory as gf

@gf.cell
def y_splitter_device():
    c = gf.Component("y_splitter")
    
    # 1. Create the main body (taper)
    # The taper provides the base shape (narrow to wide)
    taper = gf.components.taper(length=40, width1=0.3, width2=1.7)
    
    # 2. Create the slit (the triangular "hole")
    # We define a separate component to hold the triangle so we can position it 
    # relative to the taper before performing the boolean operation.
    hole_comp = gf.Component("hole")
    triangle = hole_comp << gf.components.triangle(x=35, y=1.2, layer=(1, 0))
    
    # Position the triangle: move it to the right to preserve the input waveguide section
    triangle.movex(5)
    
    # 3. Perform the boolean subtraction
    # gf.boolean takes two components and returns a new component
    final_geometry = gf.boolean(taper, hole_comp, operation="not", layer=(1, 0))
    
    # 4. Add the resulting geometry to our component
    c << final_geometry
    
    return c

if __name__ == "__main__":
    # Create the component
    device = y_splitter_device()
    
    # Save the file
    device.write_gds("y_splitter.gds")
    
    # Display in KLayout (if installed)
    device.show()
    print("GDS file 'y_splitter.gds' has been generated.")