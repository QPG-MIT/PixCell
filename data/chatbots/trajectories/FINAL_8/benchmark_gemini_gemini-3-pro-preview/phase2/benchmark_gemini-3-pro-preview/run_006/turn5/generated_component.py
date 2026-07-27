import gdsfactory as gf
import numpy as np

@gf.cell
def device_parametric():
    """
    Constructs a multi-waveguide directional coupler with adiabatic outer structures.
    
    Features:
    - Central bundle of 5 straight waveguides.
    - Outer blocks with "rails" defined by slots.
    - The outer blocks and their internal slots curve adiabatically away from the center
      at the ends, maximizing coupling in the middle and decoupling at the ports.
    - Fits within 120um x 4um footprint.
    """
    c = gf.Component()

    # --- Dimensions & Parameters ---
    length = 120.0
    
    # Waveguide dimensions
    w_wg = 0.15
    g_wg = 0.15
    pitch = w_wg + g_wg
    
    layer_wg = (1, 0)
    
    # --- 1. Central Waveguide Bundle ---
    # 5 straight waveguides centered at y=0
    n_center = 5
    xs_center = gf.cross_section.cross_section(width=w_wg, layer=layer_wg)
    
    for i in range(-(n_center // 2), (n_center // 2) + 1):
        wg = c << gf.components.straight(length=length, cross_section=xs_center)
        wg.movey(i * pitch)
    
    # Y-coordinate of the top edge of the central bundle
    # Center index 0. Top index +2. Center y = 2*pitch. Top edge = 2*pitch + w/2.
    y_center_top_edge = (n_center // 2) * pitch + w_wg / 2

    # --- 2. Outer Adiabatic Blocks ---
    # Parameters for the outer structures
    gap_min = 0.15          # Minimum coupling gap at the center
    flare_height = 0.35     # How much the block curves away at the ends
    block_thickness = 0.8   # Thickness of the solid block (rails + bulk)
    
    # Base Y position (closest point to center)
    y_block_start = y_center_top_edge + gap_min

    def create_curved_slotted_block():
        """
        Generates the outer block geometry.
        The block is defined by an inner curve and an outer curve.
        Slots are subtracted from the block to create the 'rails'.
        """
        # Generate the adiabatic curve profile (Cosine shape)
        # 1 at ends (x=0, L), 0 at center (x=L/2)
        # This creates the flare-out effect at the device edges.
        num_pts = 601
        x = np.linspace(0, length, num_pts)
        curve_factor = 0.5 * (1 + np.cos(2 * np.pi * x / length))
        
        # Calculate the Y-offsets for the curves
        # y_curve follows the inner edge of the block
        y_curve = y_block_start + flare_height * curve_factor
        
        # 1. Create the Solid Body
        # The body spans from the inner curve to the outer curve.
        # We keep constant vertical thickness to maintain bulk integrity.
        y_outer = y_curve + block_thickness
        
        pts_bot = np.stack((x, y_curve), axis=1)
        pts_top = np.stack((x[::-1], y_outer[::-1]), axis=1)
        pts_solid = np.concatenate((pts_bot, pts_top))
        
        solid = gf.Component()
        solid.add_polygon(pts_solid, layer=layer_wg)
        
        # 2. Create the Slots (to be subtracted)
        # We define slots relative to the curved baseline `y_curve`.
        # Configuration: Rail 1, Slot 1, Rail 2, Slot 2, Bulk...
        # Rail height = w_wg, Slot height = g_wg
        
        slots = gf.Component()
        
        # Slot 1: Separates Rail 1 from Rail 2
        # Bottom of slot = Rail 1 top = w_wg
        y_s1_bot = y_curve + w_wg
        y_s1_top = y_s1_bot + g_wg
        
        pts_s1 = np.concatenate((
            np.stack((x, y_s1_top), axis=1),
            np.stack((x[::-1], y_s1_bot[::-1]), axis=1)
        ))
        slots.add_polygon(pts_s1, layer=layer_wg)
        
        # Slot 2: Separates Rail 2 from Bulk
        # Bottom of slot = Rail 2 top = w_wg + g_wg + w_wg
        y_s2_bot = y_s1_top + w_wg
        y_s2_top = y_s2_bot + g_wg
        
        pts_s2 = np.concatenate((
            np.stack((x, y_s2_top), axis=1),
            np.stack((x[::-1], y_s2_bot[::-1]), axis=1)
        ))
        slots.add_polygon(pts_s2, layer=layer_wg)
        
        # 3. Boolean Subtraction
        return gf.boolean(solid, slots, operation="not", layer=layer_wg)

    # Instantiate Top Block
    top_block_cmp = create_curved_slotted_block()
    c.add_ref(top_block_cmp)
    
    # Instantiate Bottom Block (Mirrored)
    bot_ref = c << top_block_cmp
    bot_ref.mirror(p1=(0, 0), p2=(1, 0)) # Mirror across X-axis

    # --- 3. Ports ---
    c.add_port("o1", center=(0, 0), width=w_wg, orientation=180, layer=layer_wg)
    c.add_port("o2", center=(length, 0), width=w_wg, orientation=0, layer=layer_wg)

    return c

if __name__ == "__main__":
    component = device_parametric()
    component.write_gds("parametric_coupler_v2.gds")