import gdsfactory as gf
import numpy as np

@gf.cell
def directional_coupler_4x240():
    """
    Creates a directional coupler fitting a 4um x 240um footprint.
    Consists of a central coupling region and S-bend inputs/outputs.
    """
    c = gf.Component()
    
    # 1. Define Dimensions based on constraints
    total_length = 240.0
    total_height = 4.0
    wg_width = 0.5
    gap = 0.2
    
    # Calculate subsection lengths
    # We allocate 140um for the straight coupling region
    coupling_length = 140.0 
    # Remaining length split between input and output S-bends
    bend_length = (total_length - coupling_length) / 2  # 50.0 um
    
    # Calculate Vertical Offsets (Y-axis)
    # Inner: Center positions of waveguides in the coupling region
    # Distance from y=0 is half the (width + gap)
    y_center_inner = (wg_width + gap) / 2  # 0.35 um
    
    # Outer: Center positions of waveguides at input/output ports
    # Total height is 4.0um, so top edge is +2.0um. Center is 2.0 - half_width.
    y_center_outer = (total_height / 2) - (wg_width / 2) # 1.75 um
    
    # The vertical shift required for the S-bend
    dy = y_center_outer - y_center_inner # 1.4 um

    # 2. Define Cross Section
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))

    # 3. Create Central Coupling Region
    # coupler_straight creates two parallel waveguides
    # Standard ports: o1 (Top-Left), o2 (Top-Right), o3 (Bot-Left), o4 (Bot-Right)
    coupler = c << gf.components.coupler_straight(
        length=coupling_length, 
        gap=gap, 
        cross_section=xs
    )

    # 4. Create S-Bend Primitive
    # We define one S-bend and reuse it by mirroring/rotating
    # Size defines the (dx, dy) of the bend
    s_bend = gf.components.bend_s(
        size=(bend_length, dy), 
        cross_section=xs
    )

    # 5. Connect Components
    
    # --- Right Side (Outputs) ---
    # Top Right Bend: Connects to Top-Right of coupler (o2)
    sb_tr = c << s_bend
    sb_tr.connect("o1", coupler.ports["o2"]) 
    
    # Bottom Right Bend: Connects to Bot-Right of coupler (o4)
    # We mirror vertically to bend downwards
    sb_br = c << s_bend
    sb_br.mirror_y() 
    sb_br.connect("o1", coupler.ports["o4"]) 

    # --- Left Side (Inputs) ---
    # Top Left Bend: Connects to Top-Left of coupler (o1)
    # We mirror horizontally so the bend extends to the left
    sb_tl = c << s_bend
    sb_tl.mirror_x() 
    sb_tl.connect("o1", coupler.ports["o1"]) 
    
    # Bottom Left Bend: Connects to Bot-Left of coupler (o3)
    # Mirror X (to go left) and Y (to go down)
    sb_bl = c << s_bend
    sb_bl.mirror_x() 
    sb_bl.mirror_y() 
    sb_bl.connect("o1", coupler.ports["o3"]) 

    # 6. Expose External Ports
    c.add_port("o1", port=sb_tl.ports["o2"]) # Input Top
    c.add_port("o2", port=sb_bl.ports["o2"]) # Input Bottom
    c.add_port("o3", port=sb_tr.ports["o2"]) # Output Top
    c.add_port("o4", port=sb_br.ports["o2"]) # Output Bottom

    return c

if __name__ == "__main__":
    # Generate the device
    device = directional_coupler_4x240()
    
    # Write GDS
    gds_path = "directional_coupler_4x240.gds"
    device.write_gds(gds_path)
    print(f"GDS file saved to: {gds_path}")

    # Robust Size Printing (Fix for AttributeError)
    try:
        # Calculate size from bounding box (numpy array [[minx, miny], [maxx, maxy]])
        bbox = device.bbox
        width = bbox[1][0] - bbox[0][0]
        height = bbox[1][1] - bbox[0][1]
        print(f"Device Footprint: {width:.2f} um x {height:.2f} um")
    except Exception as e:
        print(f"Could not print dimensions automatically: {e}")