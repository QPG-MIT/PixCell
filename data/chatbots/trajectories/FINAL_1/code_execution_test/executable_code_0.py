import cv2
import numpy as np
from PIL import Image

# Load the image
img = cv2.imread('input_file_0.png', cv2.IMREAD_GRAYSCALE)
height, width = img.shape
print(f"Image dimensions: {width}x{height}")

# Threshold to get the black silhouette
_, thresh = cv2.threshold(img, 127, 255, cv2.THRESH_BINARY_INV)

# Find coordinates of non-zero pixels
y, x = np.where(thresh > 0)
x_min, x_max = x.min(), x.max()
y_min, y_max = y.min(), y.max()

print(f"Bounding box: x=[{x_min}, {x_max}], y=[{y_min}, {y_max}]")
print(f"Aspect ratio of black part: {(x_max - x_min) / (y_max - y_min)}")

# Scale factors
target_width_um = 40.0
target_height_um = 1.7
# Note: the prompt says "Footprint: 40.0um x 1.7um".
# This matches the aspect ratio roughly?
# width/height = 40/1.7 = 23.53
# Our image aspect ratio: (x_max - x_min) / (y_max - y_min)
actual_aspect_ratio = (x_max - x_min) / (y_max - y_min)
print(f"Target aspect ratio: {target_width_um / target_height_um}")
print(f"Image aspect ratio: {actual_aspect_ratio}")

# Let's look at the vertical profiles at some x positions
profiles = []
for x_pos in [x_min, (x_min + x_max) // 4, (x_min + x_max) // 2, 3 * (x_min + x_max) // 4, x_max]:
    profile = thresh[:, x_pos]
    profiles.append((x_pos, profile))

# To visualize where things are
import matplotlib.pyplot as plt
plt.figure(figsize=(15, 5))
plt.imshow(thresh, cmap='gray')
plt.axvline(x_min, color='r')
plt.axvline(x_max, color='r')
for xp, _ in profiles:
    plt.axvline(xp, color='g', linestyle='--')
plt.savefig('analysis.png')
