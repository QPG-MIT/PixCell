import gdsfactory as gf

@gf.cell
def get_stadium_component(width, height):
    """Creates a stadium shape (rectangle with semi-circles at ends)."""
    c = gf.Component()
    rect_w = width - height
    
    # Central rectangle
    c << gf.components.rectangle(size=(rect_w, height), centered=True)
    # Circular ends
    c1 = c << gf.components.circle(radius=height / 2)
    c1.movex(-rect_w / 2)
    c2 = c << gf.components.circle(radius=height / 2)
    c2.movex(rect_w / 2)
    return c

@gf.cell
def custom_device():
    c = gf.Component()
    
    # --- Dimensions ---
    total_w, total_h = 5.5, 3.0
    stroke = 0.4
    
    # Rung dimensions
    rung_w, rung_h = 1.2, 1.8
    rung_gap = 0.4
    
    # Rail dimensions (horizontal bars connecting rungs to frame)
    rail_h = 0.4 # Same as stroke
    # Calculate rail length to fit inside the inner stadium curve
    rail_w = total_w - 2 * stroke
    
    # 1. Create Frame (Outer Stadium - Inner Stadium)
    outer = get_stadium_component(width=total_w, height=total_h)
    inner = get_stadium_component(width=total_w - 2 * stroke, height=total_h - 2 * stroke)
    frame = gf.boolean(outer, inner, operation="not", layer=(1, 0))
    c << frame
    
    # 2. Create Two Central Rungs
    # We place these slightly offset from center to create the gap
    r1 = c << gf.components.rectangle(size=(rung_w, rung_h), centered=True)
    r1.movex(-(rung_gap / 2 + rung_w / 2))
    
    r2 = c << gf.components.rectangle(size=(rung_w, rung_h), centered=True)
    r2.movex((rung_gap / 2 + rung_w / 2))
    
    # 3. Create Horizontal Rails (Top and Bottom)
    # These create the "ladder" effect connecting the rungs to the outer frame
    # Top rail
    top_rail = c << gf.components.rectangle(size=(rail_w, rail_h), centered=True)
    top_rail.movey(rung_h / 2 - rail_h / 2)
    
    # Bottom rail
    bot_rail = c << gf.components.rectangle(size=(rail_w, rail_h), centered=True)
    bot_rail.movey(-(rung_h / 2 - rail_h / 2))
    
    return c

# Generate, save, and show
device = custom_device()
device.write_gds("device.gds")
device.show()