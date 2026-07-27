import gdsfactory as gf

@gf.cell
def my_device():
    c = gf.Component("my_device")

    # Define key parameters based on the image analysis
    base_width = 30  # Width of the main rectangle - adjusted based on raster
    base_height = 10 # Height of the main rectangle - adjusted based on raster
    stub_height = 4 # Height of the small rectangle at the bottom
    stub_width = 4 # Width of the small rectangle at the bottom
    pillar_width = 2 # Width of each pillar
    pillar_height = 8 # Total height of the pillar
    left_pillar_spacing = 3 # Spacing between left pillars

    # 1. Main Rectangle
    main_rect = gf.components.rectangle(size=(base_width, base_height), layer=(1, 0))
    main_ref = c << main_rect

    # 2. Bottom Stub
    stub = gf.components.rectangle(size=(stub_width, stub_height), layer=(1, 0))
    stub_ref = c << stub
    stub_ref.movex(base_width / 2 - stub_width / 2)  # Centered
    stub_ref.movey(-base_height / 2 - stub_height / 2) # Below the main rect

    # 3. Pillars (Left)
    pillar1 = gf.components.rectangle(size=(pillar_width, pillar_height), layer=(1, 0))
    pillar1_ref = c << pillar1
    pillar1_ref.movex(-base_width/2 + pillar_width/2)
    pillar1_ref.movey(base_height/2 + pillar_height/2)

    pillar2 = gf.components.rectangle(size=(pillar_width, pillar_height), layer=(1, 0))
    pillar2_ref = c << pillar2
    pillar2_ref.movex(-base_width/2 + pillar_width/2 + left_pillar_spacing)
    pillar2_ref.movey(base_height/2 + pillar_height/2)

    # 4. Pillars (Right - Small)
    small_pillar_width = 4
    small_pillar_height = 3

    pillar3 = gf.components.rectangle(size=(small_pillar_width, small_pillar_height), layer=(1, 0))
    pillar3_ref = c << pillar3
    pillar3_ref.movex(0) # Approximately centered, adjust as needed
    pillar3_ref.movey(base_height/2 + pillar_height/2 - 4) #adjust height position
    
    pillar4 = gf.components.rectangle(size=(small_pillar_width, small_pillar_height), layer=(1, 0))
    pillar4_ref = c << pillar4
    pillar4_ref.movex(small_pillar_width) # Approximately centered, adjust as needed
    pillar4_ref.movey(base_height/2 + pillar_height/2 - 4) #adjust height position
        
    return c

device = my_device()
device.show()
device.write_gds("my_device.gds")