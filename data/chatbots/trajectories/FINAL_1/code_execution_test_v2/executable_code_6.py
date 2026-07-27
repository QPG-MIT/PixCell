# Check segments at small x to find where things change
for x in range(0, 300, 20):
    segs = get_segments(mask[:, x])
    print(f"x={x}: {segs}")
