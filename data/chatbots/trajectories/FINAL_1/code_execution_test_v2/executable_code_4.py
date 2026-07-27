# Find the first x where the outer segments appear
for x in range(cmin, cmin + 200):
    segs = get_segments(mask[:, x])
    if len(segs) >= 3:
        print(f"Outer waveguides start at x = {x} (relative: {(x - cmin) / content_w:.3f})")
        break
