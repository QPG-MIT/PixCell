import gdsfactory as gf

def create_stadium(length, radius, layer=(1, 0)):
    """Helper function to create a solid stadium shape from primitives."""
    # Main rectangular body
    rect = gf.components.rectangle(size=(length, 2 * radius), centered=True, layer=layer)
    
    # End caps (semicircles) built from circles
    circ = gf.components.circle(radius=radius, layer=layer)
    
    cap_left = gf.Component()
    cap_left.add_ref(circ).move((-length / 2, 0))
    
    cap_right = gf.Component()
    cap_right.add_ref(circ).move((length / 2, 0))
    
    # Boolean union to fuse them seamlessly (must explicitly pass 'layer')
    u1 = gf.boolean(rect, cap_left, operation='or', layer=layer)
    stadium_comp = gf.boolean(u1, cap_right, operation='or', layer=layer)
    return stadium_comp

@gf.cell
def racetrack_filter():
    layer = (1, 0)
    
    # 1. Outer Dimensions based on the 3.0 x 5.5 footprint constraint
    # Total Width = length + 2*radius_out = 2.5 + 2*(1.5) = 5.5
    # Total Height = 2*radius_out = 2*(1.5) = 3.0
    length = 2.5
    radius_out = 1.5
    radius_in = 1.1  # Gives an outer track width of 0.4
    
    outer_solid = create_stadium(length=length, radius=radius_out, layer=layer)
    inner_void = create_stadium(length=length, radius=radius_in, layer=layer)
    
    # Create the outer hollow track ring
    track = gf.boolean(outer_solid, inner_void, operation='not', layer=layer)

    # 2. Define inner MZ arms
    arm_width = 0.2
    xs = gf.cross_section.cross_section(width=arm_width, layer=layer)
    
    # Paths for the inner arms that diverge into the outer bounds
    # Starting/ending at x=2.55 places the tips right in the middle of the curved track
    p_top = gf.Path([(-2.55, 0), (-1.2, 0.5), (1.2, 0.5), (2.55, 0)])
    arm_top = gf.path.extrude(p_top, cross_section=xs)
    
    p_bot = gf.Path([(-2.55, 0), (-1.2, -0.5), (1.2, -0.5), (2.55, 0)])
    arm_bot = gf.path.extrude(p_bot, cross_section=xs)
    
    # 3. Create the external blocks for the central straight sections
    block = gf.components.rectangle(size=(1.6, 0.4), centered=True, layer=layer)
    
    b_top_ref = gf.Component()
    b_top_ref.add_ref(block).move((0, 0.5))
    
    b_bot_ref = gf.Component()
    b_bot_ref.add_ref(block).move((0, -0.5))
    
    # Sequentially merge arms and blocks with the track via boolean unions
    solid_1 = gf.boolean(track, arm_top, operation='or', layer=layer)
    solid_2 = gf.boolean(solid_1, arm_bot, operation='or', layer=layer)
    solid_3 = gf.boolean(solid_2, b_top_ref, operation='or', layer=layer)
    device_solid = gf.boolean(solid_3, b_bot_ref, operation='or', layer=layer)

    # 4. Create internal cutouts/holes to subtract from the blocks
    # Using smaller rects placed to leave a visible "chain-link" frame
    hole = gf.components.rectangle(size=(0.6, 0.2), centered=True, layer=layer)
    
    holes_comp = gf.Component()
    # Top block holes
    holes_comp.add_ref(hole).move((-0.4, 0.5))
    holes_comp.add_ref(hole).move((0.4, 0.5))
    # Bottom block holes
    holes_comp.add_ref(hole).move((-0.4, -0.5))
    holes_comp.add_ref(hole).move((0.4, -0.5))

    # Final boolean subtraction to hollow out the blocks internally
    final_device = gf.boolean(device_solid, holes_comp, operation='not', layer=layer)

    return final_device

# Instantiate and export to GDS
if __name__ == "__main__":
    c = racetrack_filter()
    c.write_gds("racetrack_filter.gds") # Writes the file to disk for automated evaluation