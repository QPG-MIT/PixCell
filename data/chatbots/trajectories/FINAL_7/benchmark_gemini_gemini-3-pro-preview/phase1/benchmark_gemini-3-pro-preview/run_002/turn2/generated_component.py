import gdsfactory as gf
import numpy as np

@gf.cell
def device_racetrack_heaters():
    c = gf.Component()

    # =======================================================================
    # 1. Dimensions & Global Parameters
    # =======================================================================
    # Device Footprint: 5.5um x 3.0um
    h_device = 3.0
    w_device = 5.5
    
    # --- Outer Ring ---
    w_ring = 0.5
    # Radius calculated from height: (3.0 - 0.5) / 2 = 1.25
    r_ring = (h_device - w_ring) / 2.0
    # Straight length calculated from width: 5.5 - 3.0 = 2.5
    l_straight = w_device - h_device
    
    # --- Inner Structure ---
    # To look like the original image, the inner structures must be nested
    # concentrically inside the ring.
    
    # Gap estimation from image (~0.2um gap between ring and inner wire)
    gap_ring_to_inner = 0.2
    w_inner_wire = 0.15
    
    # Calculate inner radius to be concentric
    # Outer Ring Inner Edge = r_ring - w_ring/2 = 1.0
    # Inner Wire Outer Edge = 1.0 - gap_ring_to_inner = 0.8
    # Inner Wire Center Radius = 0.8 - w_inner_wire/2 = 0.725
    r_inner = 0.725
    
    # Pad dimensions
    w_inner_pad = 0.45   # Thicker pad near center
    l_pad = 0.6          # Length of the rectangular pad
    l_taper = 0.4        # Length of the taper
    
    # Gap between the left and right inner structures (horizontal gap at center)
    gap_center = 0.3
    
    # Calculate required extension length so the bend starts exactly at x = l_straight/2
    # The total length from center (x=0) to bend start (x=1.25) is:
    # (gap/2) + l_pad + l_taper + l_extension = l_straight/2
    x_start = gap_center / 2.0
    l_extension = (l_straight / 2.0) - x_start - l_pad - l_taper
    
    # If parameters force negative extension, clamp to 0 (though dimensions above should be safe)
    l_extension = max(0.0, l_extension)
    
    # Bend angle for the inner wires (they don't go full 90 deg quadrant, they stop short)
    bend_angle_inner = 65

    # =======================================================================
    # 2. Cross Sections
    # =======================================================================
    # Define radius in cross_section to allow tight bends without validation errors
    
    xs_ring = gf.cross_section.cross_section(
        width=w_ring, 
        layer=(1, 0),
        radius=r_ring 
    )
    
    xs_pad = gf.cross_section.cross_section(
        width=w_inner_pad, 
        layer=(1, 0)
    )
    
    xs_wire = gf.cross_section.cross_section(
        width=w_inner_wire, 
        layer=(1, 0),
        radius=r_inner
    )

    # =======================================================================
    # 3. Build Outer Ring
    # =======================================================================
    # Top Straight
    wg_top = c << gf.components.straight(length=l_straight, cross_section=xs_ring)
    wg_top.move((-l_straight/2, r_ring))
    
    # Bottom Straight
    wg_bot = c << gf.components.straight(length=l_straight, cross_section=xs_ring)
    wg_bot.move((-l_straight/2, -r_ring))
    
    # Right Bend (Clockwise 180 deg)
    bend_r = c << gf.components.bend_circular(radius=r_ring, angle=-180, cross_section=xs_ring)
    bend_r.connect("o1", wg_top.ports["o2"])
    
    # Left Bend (Clockwise 180 deg)
    bend_l = c << gf.components.bend_circular(radius=r_ring, angle=-180, cross_section=xs_ring)
    bend_l.connect("o1", wg_bot.ports["o1"])

    # =======================================================================
    # 4. Build Inner Structures
    # =======================================================================
    # We create a "quadrant arm" and replicate it 4 times.
    
    def create_arm():
        arm = gf.Component()
        
        # 1. Pad
        p = arm << gf.components.straight(length=l_pad, cross_section=xs_pad)
        
        # 2. Taper
        t = arm << gf.components.taper(
            length=l_taper, 
            width1=w_inner_pad, 
            width2=w_inner_wire,
            layer=(1, 0)
        )
        t.connect("o1", p.ports["o2"])
        
        # 3. Extension (Straight wire to reach bend point)
        current_port = t.ports["o2"]
        if l_extension > 0.001:
            ext = arm << gf.components.straight(length=l_extension, cross_section=xs_wire)
            ext.connect("o1", t.ports["o2"])
            current_port = ext.ports["o2"]
            
        # 4. Concentric Bend
        # Radius matches the vertical offset, ensuring center of curvature is at y=0
        b = arm << gf.components.bend_circular(
            radius=r_inner, 
            angle=-bend_angle_inner, 
            cross_section=xs_wire
        )
        b.connect("o1", current_port)
        
        arm.add_port("o1", port=p.ports["o1"])
        return arm

    # Create the template
    arm_template = create_arm()
    
    # The straight part of the arm is at y = r_inner. 
    # This ensures the bend (radius = r_inner) curves around a center at y=0.
    y_pos = r_inner
    x_pos = gap_center / 2.0
    
    # -- Top Right --
    tr = c << arm_template
    tr.move((x_pos, y_pos))
    
    # -- Bottom Right -- 
    # Mirror Top-Right across X-axis
    br = c << arm_template
    br.mirror(p1=(0,0), p2=(1,0))
    br.move((x_pos, -y_pos))
    
    # -- Top Left --
    # Mirror Top-Right across Y-axis
    tl = c << arm_template
    tl.mirror(p1=(0,0), p2=(0,1))
    tl.move((-x_pos, y_pos))
    
    # -- Bottom Left --
    # Rotate Top-Right 180 degrees
    bl = c << arm_template
    bl.rotate(180)
    bl.move((-x_pos, -y_pos))

    return c

if __name__ == "__main__":
    device = device_racetrack_heaters()
    device.write_gds("racetrack_heaters.gds")