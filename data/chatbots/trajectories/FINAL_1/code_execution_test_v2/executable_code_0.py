import PIL.Image
import PIL.ImageDraw

# Load the image to get dimensions and inspect
img = PIL.Image.open('input_file_0.png')
width, height = img.size
print(f"Image dimensions: {width}x{height}")

# Let's find the bounding box of the black pixels to determine relative proportions
import numpy as np
img_array = np.array(img.convert('L'))
# Black is 0, white is 255.
# Let's threshold it.
mask = img_array < 128
rows = np.any(mask, axis=1)
cols = np.any(mask, axis=0)
rmin, rmax = np.where(rows)[0][[0, -1]]
cmin, cmax = np.where(cols)[0][[0, -1]]

print(f"Content bounding box: rows {rmin} to {rmax}, cols {cmin} to {cmax}")
content_h = rmax - rmin
content_w = cmax - cmin
print(f"Content dimensions: {content_w}x{content_h}")

# Aspect ratio of content:
print(f"Aspect ratio: {content_w / content_h:.2f}")

# Target aspect ratio from footprint: 40 / 1.7 = 23.53
target_ar = 40.0 / 1.7
print(f"Target aspect ratio: {target_ar:.2f}")

# The image might have some padding or different aspect ratio.
# Let's look at the central taper length.
# Scan the middle row to find where the central taper ends.
mid_y = (rmin + rmax) // 2
mid_row = mask[mid_y, :]
# Find the start and end of the middle black part.
# The middle part is at the left edge.
# Let's look at a vertical slice at some x.
# At x = cmin + 10
slice_x = cmin + 10
vert_slice = mask[:, slice_x]
# Find gaps.
# Let's find all contiguous black segments in this slice.
def get_segments(arr):
    segs = []
    start = None
    for i, val in enumerate(arr):
        if val and start is None:
            start = i
        elif not val and start is not None:
            segs.append((start, i-1))
            start = None
    if start is not None:
        segs.append((start, len(arr)-1))
    return segs

segs_left = get_segments(mask[:, cmin + 5])
print(f"Segments at left: {segs_left}")

# Find where central taper ends.
# It's the segment that's in the middle.
central_segment_exists = True
x_taper_end = cmin
for x in range(cmin, cmax):
    segs = get_segments(mask[:, x])
    # Central segment is usually the middle one if there are 3, or none if it ended.
    # Looking at the image, there are 3 at the left, 2 at the right.
    if len(segs) < 3:
        x_taper_end = x
        break
print(f"Central taper ends at x = {x_taper_end} (relative: {(x_taper_end - cmin) / content_w:.2f})")

# Find where the curves start/end.
# Outer waveguides:
# At the right end:
segs_right = get_segments(mask[:, cmax - 5])
print(f"Segments at right: {segs_right}")
