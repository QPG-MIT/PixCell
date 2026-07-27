import gdsfactory as gf

@gf.cell
def device():
    """
    Creates two interlocking U-shaped waveguides.
    Top U-bend opens downward, bottom U-bend opens upward.
    Footprint: approximately 120 x 4 um
    """
    c = gf.Component()
    
    # Parameters
    wg_width = 0.5  # Waveguide width in um
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))
    
    # Dimensions to achieve 120 x 4 um footprint
    straight_len_top = 58  # Length of straight sections
    straight_len_bottom = 43  # Offset for bottom structure
    bend_radius = 1.5  # Radius of U-bends
    vertical_separation = 1.5  # Vertical offset from center
    horizontal_offset = 15  # Horizontal offset between structures
    
    # Top U-bend (opening downward)
    # Path: straight right -> bend down 180° -> straight right
    top_path = gf.Path()
    top_path += gf.path.straight(length=straight_len_top)
    top_path += gf.path.arc(radius=bend_radius, angle=-180)
    top_path += gf.path.straight(length=straight_len_top - horizontal_offset)
    
    top_structure = c << gf.path.extrude(top_path, cross_section=xs)
    top_structure.movey(vertical_separation)
    
    # Bottom U-bend (opening upward)
    # Path: straight right -> bend up 180° -> straight right
    bottom_path = gf.Path()
    bottom_path += gf.path.straight(length=straight_len_bottom)
    bottom_path += gf.path.arc(radius=bend_radius, angle=180)
    bottom_path += gf.path.straight(length=straight_len_top)
    
    bottom_structure = c << gf.path.extrude(bottom_path, cross_section=xs)
    bottom_structure.movey(-vertical_separation)
    
    return c

# Create the device and save
if __name__ == "__main__":
    device_component = device()
    device_component.write_gds("device.gds")
    print("GDS file 'device.gds' has been generated successfully!")