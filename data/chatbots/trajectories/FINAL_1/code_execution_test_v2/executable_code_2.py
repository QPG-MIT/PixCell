# Check segments at different x positions
for x_rel in [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]:
    x = int(cmin + x_rel * content_w)
    segs = get_segments(mask[:, x])
    print(f"Segments at x_rel {x_rel:.1f} (x={x}): {segs}")
