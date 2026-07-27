import gdsfactory as gf

@gf.cell
def recreated_device():
    """
    Recreates the photonic device geometry from the provided image.
    Footprint: 18.24um x 0.7um
    
    Fix: Explicitly set radius_min to 0.01 in the CrossSection to override 
    the default 10um limit, allowing the sub-micron U-turns.
    """
    c = gf.Component("recreated_device")
    
    # --- Geometrical Constants to fit 0.7um height ---
    w = 0.06           # Waveguide width
    g_inner = 0.08     # Gap to central line
    g_outer = 0.12     # Gap inside the hook
    # Total height = 4*w + 2*g_inner + 2*g_outer + w (center) 
    # = 0.24 + 0.16 + 0.24 + 0.06 = 0.7um
    
    # --- Define Cross Section with Overridden Bend Radius Constraint ---
    # Setting radius_min=0.01 allows the 0.09um radius required for the hook
    xs = gf.cross_section.cross_section(width=w, radius_min=0.01)
    
    # Longitudinal dimensions to fit ~18.24um width
    l_inner = 10.5
    l_extension = 3.5
    l_taper = 1.0
    r_bend = (g_outer + w) / 2  # This is 0.09um
    
    def create_hook():
        h = gf.Component()
        
        # 1. Inner straight waveguide
        inner = h << gf.components.straight(length=l_inner, cross_section=xs)
        
        # 2. Grating structure on the inner arm
        # Using parametric rectangles
        for i in range(50):
            bar = h << gf.components.rectangle(size=(0.04, 0.1))
            # Position relative to inner arm center
            bar.x = i * 0.18 - l_inner/2 + 1.5
            bar.y = w/2 + 0.05
            
        # 3. 180-degree U-bend
        # Uses the custom cross_section to bypass the 10um radius check
        bend = h << gf.components.bend_circular(radius=r_bend, angle=180, cross_section=xs)
        bend.connect("o1", inner.ports["o2"])
        
        # 4. Outer straight waveguide
        outer = h << gf.components.straight(length=l_inner + l_extension, cross_section=xs)
        outer.connect("o1", bend.ports["o2"])
        
        # 5. Sharpened taper tip
        tip = h << gf.components.taper(length=l_taper, width1=w, width2=0.001)
        tip.connect("o1", outer.ports["o2"])
        
        # 6. Large radius tail at the input
        # Note: Even this 5um radius would fail the default 10um check
        tail_path = gf.path.arc(radius=5.0, angle=40)
        tail = h << gf.path.extrude(tail_path, cross_section=xs)
        tail.connect("o1", inner.ports["o1"])
        
        return h

    # --- Assemble final component with 180-degree symmetry ---
    
    # Central horizontal line
    center_line = c << gf.components.straight(length=18.24, cross_section=xs)
    center_line.x = 0
    center_line.y = 0
    
    # Top hook structure
    top_hook = c << create_hook()
    top_hook.movey(g_inner + w) # Align so gap is g_inner
    top_hook.x = 0
    
    # Bottom hook structure (180-degree rotated)
    bot_hook = c << create_hook()
    bot_hook.rotate(180)
    bot_hook.movey(-(g_inner + w))
    bot_hook.x = 0
    
    return c

if __name__ == "__main__":
    component = recreated_device()
    print(f"Resulting Footprint: {component.size_info.width:.2f} x {component.size_info.height:.2f} um")
    component.show()