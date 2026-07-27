import gdsfactory as gf
import numpy as np

@gf.cell
def recreated_device():
    """
    Recreates the device geometry based on parametric primitives.
    Total Footprint: 18.24um x 0.7um
    
    Fixes:
    - Replaced property setters (.x, .xmax) with .move() for better compatibility.
    - Used explicit reference handling to avoid 'int' attribute errors.
    - Ensured sub-micron bend radii are allowed.
    """
    c = gf.Component("device_recreation")
    
    # Constants derived from footprint
    WIDTH_TOTAL = 18.24
    WG_WIDTH = 0.06
    PITCH = 0.155  # Vertical spacing to fit 0.7um height
    LAYER = (1, 0)
    
    # Define cross-section with small radius limit
    xs = gf.cross_section.cross_section(width=WG_WIDTH, layer=LAYER, radius_min=0.01)
    
    # 1. Central horizontal waveguide
    # We create it and move its center to the center of the footprint
    center_wg = gf.components.straight(length=WIDTH_TOTAL, cross_section=xs)
    center_ref = c << center_wg
    # Move so the waveguide spans from x=0 to x=WIDTH_TOTAL at y=0
    center_ref.move(origin=center_ref.ports["o1"], destination=(0, 0))

    @gf.cell
    def make_arm_component():
        """Creates one half of the symmetric structure (straight, bend, grating, tail)."""
        a = gf.Component()
        
        l_outer = 11.0
        l_taper = 4.0
        l_grating = 11.5
        r_bend = PITCH / 2
        
        # Part A: Outer straight track with taper
        st_outer = a << gf.components.straight(length=l_outer, cross_section=xs)
        taper = a << gf.components.taper(length=l_taper, width1=WG_WIDTH, width2=0.001, layer=LAYER)
        taper.connect("o1", st_outer.ports["o1"])
        
        # Part B: 180-degree bend
        bend = a << gf.components.bend_circular(radius=r_bend, angle=180, cross_section=xs)
        bend.connect("o1", st_outer.ports["o2"])
        
        # Part C: Inner track with grating
        grat_base = gf.components.straight(length=l_grating, cross_section=xs)
        teeth = gf.Component()
        n_periods = 60
        period = l_grating / n_periods
        for i in range(n_periods):
            tooth = teeth << gf.components.rectangle(size=(period * 0.5, WG_WIDTH), layer=LAYER)
            tooth.move((i * period, -WG_WIDTH))
            
        grating = gf.boolean(grat_base, teeth, operation="not", layer=LAYER)
        g_ref = a << grating
        # Manually align grating to bend port
        g_ref.move(origin=(l_grating, 0), destination=bend.ports["o2"].center)
        
        # Part D: Curved tail
        tail = a << gf.components.bend_euler(radius=10, angle=-15, cross_section=xs)
        tail.connect("o1", destination=(g_ref.xmin, 0))
        
        return a

    # 2. Add Top Arm
    # The bend should be on the right side
    top_arm_comp = make_arm_component()
    top_ref = c << top_arm_comp
    # Position: top_ref xmax at WIDTH_TOTAL, inner track at y = PITCH
    top_ref.move(origin=(top_ref.xmax, 0), destination=(WIDTH_TOTAL, PITCH))
    
    # 3. Add Bottom Arm
    # Point symmetric: rotate 180 degrees
    bot_ref = c << top_arm_comp
    bot_ref.mirror(p1=(0,0), p2=(1,0)) # Mirror vertically
    bot_ref.mirror(p1=(0,0), p2=(0,1)) # Mirror horizontally to achieve 180 rotation
    # Position: bot_ref xmin at 0, inner track at y = -PITCH
    bot_ref.move(origin=(bot_ref.xmin, 0), destination=(0, -PITCH))
    
    return c

if __name__ == "__main__":
    component = recreated_device()
    component.show()
    component.write_gds("device_recreation.gds")