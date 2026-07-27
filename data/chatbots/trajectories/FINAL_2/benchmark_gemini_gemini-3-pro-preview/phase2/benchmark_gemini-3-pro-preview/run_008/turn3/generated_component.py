import gdsfactory as gf

@gf.cell
def device_1x4_splitter():
    c = gf.Component()
    
    # Layer definition
    layer = (1, 0)
    
    # --- Dimensions ---
    # Dimensions derived to match the visual weight and aspect ratio of the target.
    # Fits within the 25um x 10um constraint.
    
    # Main Body
    # Aspect ratio adjusted to approx 2.2:1 (Width:Height)
    body_width = 11.0
    body_height = 4.8
    
    # Top Prongs (Output)
    # Modeled as a composite structure: Tapered Base + Straight Top
    # This creates the "chimney" or "bottleneck" silhouette.
    num_prongs = 4
    prong_pitch = 2.4          # Center-to-center spacing
    
    # Base section (The neck connecting to the body)
    prong_base_len = 1.2
    prong_base_width = 1.8     # Wide base
    prong_mid_width = 1.2      # Width at the transition
    
    # Tip section (The straight vertical extension)
    prong_tip_len = 3.0
    prong_tip_width = 1.2      # Constant width (straight waveguide)
    
    # Bottom Input
    # Short, stout taper
    input_len = 1.5
    input_width_base = 2.0
    input_width_tip = 0.8

    # --- Geometry Construction ---

    # 1. Main Body
    body = c << gf.components.rectangle(
        size=(body_width, body_height), 
        layer=layer, 
        centered=True
    )

    # 2. Top Prongs (Array of 4)
    # We create two taper components: one for the neck, one for the straight part.
    # (Using taper for the straight part avoids needing to define cross_sections).
    taper_neck = gf.components.taper(
        length=prong_base_len,
        width1=prong_base_width,
        width2=prong_mid_width,
        layer=layer
    )
    
    taper_straight = gf.components.taper(
        length=prong_tip_len,
        width1=prong_tip_width,
        width2=prong_tip_width,
        layer=layer
    )
    
    for i in range(num_prongs):
        # Calculate x-offset to center the array
        # Formula: (index - (count-1)/2) * pitch
        x_pos = (i - (num_prongs - 1) / 2.0) * prong_pitch
        
        # Place Base (Neck)
        # Rotate 90 deg so it points North (+y).
        # Move so the base (Port 1) sits on the top edge of the body.
        ref_neck = c << taper_neck
        ref_neck.rotate(90)
        ref_neck.move((x_pos, body_height / 2.0))
        
        # Place Tip (Straight)
        # Connect the start of the straight section to the end of the neck.
        ref_tip = c << taper_straight
        ref_tip.connect("o1", ref_neck.ports["o2"])

    # 3. Bottom Input
    # Standard taper pointing South
    taper_input = gf.components.taper(
        length=input_len,
        width1=input_width_base,
        width2=input_width_tip,
        layer=layer
    )
    
    ref_bot = c << taper_input
    ref_bot.rotate(-90)  # Pointing South (-y)
    ref_bot.move((0, -body_height / 2.0))

    return c

if __name__ == "__main__":
    device = device_1x4_splitter()
    device.write_gds("device_1x4_splitter.gds")
    device.show()