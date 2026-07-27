import gdsfactory as gf
import numpy as np

@gf.cell
def device_generator():
    """
    Generates a directional coupler device with U-bend grating arms.
    Target footprint: 18.24 x 0.7 um.
    """
    c = gf.Component()

    # =======================================================================
    # Parameters
    # =======================================================================
    # Overall dimensions
    length = 18.24
    
    # Feature sizes derived to fit 0.7um height
    # Height calculation verification:
    # Inner Y center = w/2 + gap + w/2 = 0.03 + 0.06 + 0.03 = 0.12
    # Bend separation (center-to-center) = 2 * R
    # Outer Y center = Inner Y + 2*R
    # Top Edge = Outer Y + w/2 = 0.12 + 2*R + 0.03
    # Total Height = 2 * Top Edge = 2 * (0.15 + 2*R)
    # 0.7 = 0.3 + 4*R  =>  4*R = 0.4  =>  R = 0.1
    
    w = 0.06           # Waveguide width
    gap_coupling = 0.06 
    R = 0.1            # Bend radius
    
    # Grating parameters
    period = 0.2
    fill_factor = 0.5
    grating_length = 12.0
    buffer_length = 0.5 
    
    # Layer definition
    layer = (1, 0)
    
    # Define CrossSection with explicit radius to pass validation
    # radius=R sets the default and allows bends of this size
    xs = gf.cross_section.cross_section(width=w, layer=layer, radius=R)
    
    # =======================================================================
    # 1. Central Bus
    # =======================================================================
    bus = c << gf.components.straight(length=length, cross_section=xs)
    bus.center = (0, 0)

    # =======================================================================
    # 2. Sub-Component: Grating Arm
    # =======================================================================
    @gf.cell
    def grating_arm_component(len_grat, len_buf, p, fill, xs_ref, layer_ref):
        cmp = gf.Component()
        
        # Buffer: Solid waveguide connecting to bend
        buf = cmp << gf.components.straight(length=len_buf, cross_section=xs_ref)
        
        # Grating: Array of rectangles
        tooth_len = p * fill
        tooth_w = xs_ref.width
        
        n_periods = int(len_grat / p)
        
        # Create single tooth
        tooth = gf.components.rectangle(size=(tooth_len, tooth_w), layer=layer_ref, centered=True)
        
        # Place array starting after buffer
        # Center of first tooth is at len_buf + p/2 (since period p starts at len_buf)
        cmp.add_array(
            component=tooth,
            columns=n_periods,
            rows=1,
            spacing=(p, 0)
        ).move((len_buf + p/2.0, 0))
        
        # Expose ports
        cmp.add_port("o1", port=buf.ports["o1"]) 
        # Add a dummy output port for alignment calculation
        cmp.add_port("o2", center=(len_buf + n_periods*p, 0), width=tooth_w, orientation=0, layer=layer_ref)
        
        return cmp

    # =======================================================================
    # 3. Sub-Component: U-Structure
    # =======================================================================
    @gf.cell
    def u_structure():
        u = gf.Component()
        
        # 180-degree Bend
        # Creates C-shape: o1 at (0,0), o2 at (0, 2R)
        bend = u << gf.components.bend_circular(radius=R, angle=180, cross_section=xs)
        
        # Inner Arm (Grating)
        # Connect to o1 (bottom port of the bend)
        g_arm = u << grating_arm_component(
            len_grat=grating_length, 
            len_buf=buffer_length, 
            p=period, 
            fill=fill_factor,
            xs_ref=xs,
            layer_ref=layer
        )
        g_arm.connect("o2", bend.ports["o1"])
        
        # Outer Arm (Solid + Taper)
        # Length calculation to keep total length roughly aligned with device length
        # Taper tip should end near x = -length/2 (relative to device center)
        # Bend center is at x = length/2 - R.
        # Arm length needed approx length - R.
        solid_len_total = length - R 
        taper_len = 2.0
        straight_len = solid_len_total - taper_len - 0.5 # Sub 0.5 for aesthetic margin
        
        # Straight section connecting to bend o2 (top port)
        st = u << gf.components.straight(length=straight_len, cross_section=xs)
        st.connect("o2", bend.ports["o2"])
        
        # Taper tip (w -> 0.01)
        tp = u << gf.components.taper(length=taper_len, width1=w, width2=0.01, cross_section=xs)
        tp.connect("o1", st.ports["o1"])
        
        return u

    # =======================================================================
    # 4. Assembly
    # =======================================================================
    
    # Y offset calculation for the inner grating arm
    # The grating arm is attached to bend o1.
    # In the main device, the inner arm center is at: w/2 (bus half) + gap + w/2 (arm half)
    y_inner = w/2.0 + gap_coupling + w/2.0
    
    # -- Top U-Structure --
    # Placed on top. Bend on the Right.
    # We want the connection point (inner arm) at y = +y_inner.
    # Bend circular o1 is at (0,0). So we move (0,0) to (x_loc, y_inner).
    # We want the bend arc to be at the right edge of the device (x = length/2).
    # The bend arc extends R past its ports. So port x = length/2 - R.
    top_u = c << u_structure()
    top_u.move((length/2.0 - R, y_inner))
    
    # -- Bottom U-Structure --
    # Rotated 180 degrees.
    bot_u = c << u_structure()
    bot_u.rotate(180)
    
    # After rotation:
    # Origin (was bend o1) is still at local (0,0) relative to the reference center.
    # The structure is flipped.
    # We want this origin at x = -length/2 + R, y = -y_inner.
    bot_u.move((-length/2.0 + R, -y_inner))

    return c

if __name__ == "__main__":
    device = device_generator()
    device.write_gds("directional_coupler_gratings.gds")