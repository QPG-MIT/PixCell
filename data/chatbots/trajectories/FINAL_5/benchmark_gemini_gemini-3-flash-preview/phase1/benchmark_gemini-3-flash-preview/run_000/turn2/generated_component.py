import gdsfactory as gf
import numpy as np

@gf.cell
def recreate_device():
    """
    Final high-fidelity recreation of the device.
    Solves port mismatch errors and accurately reproduces the tapered curved tails.
    """
    c = gf.Component("recreated_device_final")
    
    # --- Dimensions & Parameters ---
    TOTAL_WIDTH = 18.24
    RES_LAYER = (1, 0)
    
    # Cross-sections to ensure consistency and avoid width mismatch
    # Low radius_min is essential for the tight folds
    xs_bus = gf.cross_section.cross_section(width=0.04, layer=RES_LAYER)
    xs_rail = gf.cross_section.cross_section(width=0.06, layer=RES_LAYER, radius_min=0.01)
    xs_tip = gf.cross_section.cross_section(width=0.001, layer=RES_LAYER)
    
    # 1. Central Bus Construction
    # 'Head' is a small segment on the far left
    bus_head = c << gf.components.straight(length=0.4, width=0.08, layer=RES_LAYER)
    bus_head.xmin = -TOTAL_WIDTH / 2
    bus_head.y = 0
    
    # Bus main - connect to head. Use a taper to bridge 0.08um to 0.04um
    bus_taper = c << gf.components.taper(length=0.2, width1=0.08, width2=0.04, layer=RES_LAYER)
    bus_taper.connect("o1", bus_head.ports["o2"])
    
    bus_main = c << gf.components.straight(length=TOTAL_WIDTH - 0.6, cross_section=xs_bus)
    bus_main.connect("o1", bus_taper.ports["o2"])

    def make_arm(is_top=True):
        arm = gf.Component()
        side = 1 if is_top else -1
        
        # A. Inner Rail: Input S-bend + Grating Straight
        lead_len = 4.0
        dy = 0.15 # Displacement from center
        lead_in = arm << gf.components.bend_s(size=(lead_len, dy * side), cross_section=xs_rail)
        
        main_len = 10.5
        main_wg = arm << gf.components.straight(length=main_len, cross_section=xs_rail)
        main_wg.connect("o1", lead_in.ports["o2"])
        
        # Add high-density Grating Teeth
        n_teeth = 70
        tooth_w, tooth_h = 0.03, 0.06
        period = main_len / n_teeth
        for i in range(n_teeth):
            t = arm << gf.components.rectangle(size=(tooth_w, tooth_h), layer=RES_LAYER)
            t.x = main_wg.xmin + i * period + period/2
            if is_top:
                t.ymax = main_wg.ymin - 0.005 
            else:
                t.ymin = main_wg.ymax + 0.005
                
        # B. Tight U-turn (180 degrees)
        radius = 0.08
        b1 = arm << gf.components.bend_circular(radius=radius, angle=90, cross_section=xs_rail)
        b1.connect("o1", main_wg.ports["o2"])
        b2 = arm << gf.components.bend_circular(radius=radius, angle=90, cross_section=xs_rail)
        b2.connect("o1", b1.ports["o2"])
        
        # C. Outer Rail: Return Straight + Curved Tapered Tail
        ret_len = 9.5
        ret_wg = arm << gf.components.straight(length=ret_len, cross_section=xs_rail)
        ret_wg.connect("o1", b2.ports["o2"])
        
        # Create tail: arcs away from center (35 deg) while thinning to a point
        tail_path = gf.path.euler(radius=3.5, angle=35 * side)
        tail_trans = gf.path.transition(xs_rail, xs_tip)
        tail = arm << gf.path.extrude_transition(tail_path, tail_trans)
        tail.connect("o1", ret_wg.ports["o2"])
        
        return arm

    # --- Assembly ---
    top_arm = c << make_arm(is_top=True)
    bot_arm = c << make_arm(is_top=False)
    
    # Align to footprint
    top_arm.xmax = TOTAL_WIDTH / 2
    bot_arm.xmax = TOTAL_WIDTH / 2
    
    # Align lead-in start to the center-line of the bus
    top_arm.y = 0
    bot_arm.y = 0
    
    return c

if __name__ == "__main__":
    component = recreate_device()
    component.write_gds("final_corrected_device.gds")
    # component.show() # Open KLayout to visualize