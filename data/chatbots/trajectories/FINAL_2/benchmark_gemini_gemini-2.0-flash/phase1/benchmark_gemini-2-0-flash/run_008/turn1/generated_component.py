import gdsfactory as gf

@gf.cell
def my_device():
    c = gf.Component("my_device")  # Added component name

    # Define key parameters based on the image analysis
    base_width = 20  # Width of the main rectangle
    base_height = 5 # Height of the main rectangle
    stub_height = 2 # Height of the small rectangle at the bottom
    stub_width = 2 # Width of the small rectangle at the bottom
    pillar_width = 1.5 # Width of each pillar
    pillar_base_height = 2 # Height of the base part of the pillars
    pillar_height = 4 # Total height of the pillar

    # 1. Main Rectangle
    main_rect = gf.components.rectangle(size=(base_width, base_height), layer=(1, 0))
    main_ref = c << main_rect

    # 2. Bottom Stub
    stub = gf.components.rectangle(size=(stub_width, stub_height), layer=(1, 0))
    stub_ref = c << stub
    stub_ref.movex(base_width / 2 - stub_width / 2)  # Centered
    stub_ref.movey(-base_height / 2 - stub_height / 2) # Below the main rect

    # 3. Pillars
    pillar_x_offsets = [-base_width/2 + base_width/5, -base_width/6, base_width/6, base_width/2 - base_width/5]
    
    for x_offset in pillar_x_offsets:

        # Pillar base
        pillar_base = gf.components.rectangle(size=(pillar_width, pillar_base_height), layer=(1, 0))
        pillar_base_ref = c << pillar_base
        pillar_base_ref.movex(x_offset)
        pillar_base_ref.movey(base_height/2) # Top of the main rect

        # Pillar top
        pillar_top = gf.components.rectangle(size=(pillar_width, pillar_height - pillar_base_height), layer=(1, 0))
        pillar_top_ref = c << pillar_top
        pillar_top_ref.movex(x_offset)
        pillar_top_ref.movey(base_height/2 + (pillar_height - pillar_base_height)/2)

    return c

device = my_device()
device.show()
device.write_gds("my_device.gds")  # Added write_gds to produce the GDS file