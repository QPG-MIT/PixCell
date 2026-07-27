import gdsfactory as gf

@gf.cell
def create_tapered_splitter():
    c = gf.Component("tapered_splitter")
    
    # 1. Define Cross Sections
    # Center taper: wider to narrower
    xs_taper_start = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    xs_taper_end = gf.cross_section.cross_section(width=0.05, layer=(1, 0))
    
    # Standard waveguide for the arms
    xs_arm = gf.cross_section.cross_section(width=0.3, layer=(1, 0))
    
    # 2. Central Spike (Linear Taper)
    p_center = gf.path.straight(length=40)
    center_wg = c << gf.path.extrude_transition(
        p_center, 
        transition=gf.path.transition(xs_taper_start, xs_taper_end)
    )
    
    # 3. Outer Arms (Composite Path)
    # Define a single path that is straight then curves outwards
    p_arm = gf.Path()
    p_arm.append(gf.path.straight(length=20))
    p_arm.append(gf.path.euler(radius=25, angle=20))
    
    # Extrude the path into geometry
    arm_geo = gf.path.extrude(p_arm, cross_section=xs_arm)
    
    # 4. Placement
    # Top Arm
    top = c << arm_geo
    top.movey(0.6) # Vertical offset to separate from center
    
    # Bottom Arm (Mirror of top)
    bot = c << arm_geo
    bot.mirror(p1=(0, 0), p2=(1, 0))
    bot.movey(-0.6) # Negative offset
    
    return c

# Generate
device = create_tapered_splitter()
device.write_gds("tapered_splitter.gds")

print("GDS file 'tapered_splitter.gds' has been generated.")